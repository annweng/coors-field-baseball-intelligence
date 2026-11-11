"""Train gradient-boosted multiclass PA model with calibration."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from data_pipeline.features.cache import load_or_build_features
from data_pipeline.features.constants import OUTCOME_CLASSES
from data_pipeline.features.rolling import minimum_prior_plate_appearances
from data_pipeline.load.postgres import create_session
from data_pipeline.load.reader import load_plate_appearances_frame
from data_pipeline.settings import settings
from models.advanced.feature_matrix import append_baseline_probas, encode_matrix
from models.baseline.forecaster import BaselineForecaster
from models.evaluation.calibration import reliability_bins
from models.evaluation.compare import baseline_on_split, better_than_baseline
from models.evaluation.metrics import evaluate_multiclass
from models.evaluation.player_game import player_game_mae
from models.evaluation.splits import chronological_split

from app.db.models import ModelEvaluation
from sklearn.calibration import CalibratedClassifierCV
from sklearn.utils.class_weight import compute_sample_weight
from sqlalchemy.dialects.postgresql import insert

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("train_advanced")

MODEL_VERSION = "xgb-v0.2.2"
ARTIFACT_PATH = ROOT / "models" / "artifacts" / f"{MODEL_VERSION}.joblib"
ACTIVE_MODEL_FILE = ROOT / "models" / "artifacts" / "active_model.json"


def _get_estimator() -> object:
    from xgboost import XGBClassifier

    return XGBClassifier(
        objective="multi:softprob",
        num_class=len(OUTCOME_CLASSES),
        n_estimators=250,
        max_depth=4,
        learning_rate=0.08,
        min_child_weight=20,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_lambda=2.0,
        reg_alpha=0.1,
        random_state=42,
        n_jobs=-1,
        tree_method="hist",
        early_stopping_rounds=25,
        eval_metric="mlogloss",
    )


def _encode_labels(labels: list[str]) -> np.ndarray:
    idx = {c: i for i, c in enumerate(OUTCOME_CLASSES)}
    return np.array([idx[str(y)] for y in labels], dtype=np.int32)


def _underlying_xgb_for_export(model: object):
    if hasattr(model, "get_booster"):
        return model
    if hasattr(model, "calibrated_classifiers_"):
        return model.calibrated_classifiers_[0].estimator
    if hasattr(model, "estimator"):
        return getattr(model, "estimator")
    return None


def _order_probas(classes: list, probas: np.ndarray) -> np.ndarray:
    if classes and not isinstance(classes[0], str):
        ordered = probas[:, : len(OUTCOME_CLASSES)]
    else:
        col_map = [classes.index(c) for c in OUTCOME_CLASSES]
        ordered = probas[:, col_map]
    return ordered / ordered.sum(axis=1, keepdims=True)


def load_featured_seasons(seasons: list[int]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for season in seasons:
        raw = load_plate_appearances_frame(settings.database_url, seasons=[season])
        raw = raw[raw["outcome"] != "unknown"].copy()
        logger.info("Season %s: %s PAs from DB", season, len(raw))
        if raw.empty:
            continue
        featured = load_or_build_features(raw, season=season)
        frames.append(featured)
    if not frames:
        raise RuntimeError("No plate appearances loaded")
    return pd.concat(frames, ignore_index=True)


def train_and_evaluate(
    *,
    seasons: list[int],
    train_end: date,
    val_end: date,
    test_end: date | None,
    calibration: str | None = "sigmoid",
    compact_features: bool = True,
    stack_baseline: bool = True,
    class_balanced: bool = True,
) -> dict:
    featured = load_featured_seasons(seasons)
    eligible = featured[minimum_prior_plate_appearances(featured, min_pa=5)].copy()

    train, val, test = chronological_split(
        eligible,
        train_end=train_end,
        val_end=val_end,
        test_end=test_end,
    )
    logger.info("Splits train/val/test: %s / %s / %s", len(train), len(val), len(test))
    if test.empty:
        raise RuntimeError("Test split empty — check --test-end and loaded seasons")

    baseline_for_stack: BaselineForecaster | None = None
    if stack_baseline:
        baseline_for_stack = BaselineForecaster()
        baseline_for_stack.fit(train)
        train = append_baseline_probas(train, baseline_for_stack)
        val = append_baseline_probas(val, baseline_for_stack)
        test = append_baseline_probas(test, baseline_for_stack)

    x_train, feature_cols = encode_matrix(train, compact=compact_features)
    x_val, _ = encode_matrix(val, compact=compact_features)
    x_test, _ = encode_matrix(test, compact=compact_features)
    y_train = train["outcome"].tolist()
    y_val = val["outcome"].tolist()
    y_test = test["outcome"].tolist()

    y_train_i = _encode_labels(y_train)
    y_val_i = _encode_labels(y_val)

    sample_weight = None
    if class_balanced:
        sample_weight = compute_sample_weight(class_weight="balanced", y=y_train)

    base = _get_estimator()
    base.fit(
        x_train,
        y_train_i,
        sample_weight=sample_weight,
        eval_set=[(x_val, y_val_i)],
        verbose=False,
    )

    if calibration:
        try:
            from sklearn.frozen import FrozenEstimator

            model = CalibratedClassifierCV(FrozenEstimator(base), method=calibration)
        except ImportError:
            model = CalibratedClassifierCV(base, method=calibration, cv="prefit")
        model.fit(x_val, y_val_i)
        probas_test = _order_probas(list(model.classes_), model.predict_proba(x_test))
    else:
        model = base
        probas_test = _order_probas(list(range(len(OUTCOME_CLASSES))), model.predict_proba(x_test))
    test_metrics = evaluate_multiclass(y_test, probas_test)
    baseline_metrics = baseline_on_split(train, test)
    test_metrics["player_game"] = player_game_mae(test, probas_test)
    test_metrics["calibration_hr"] = reliability_bins(y_test, probas_test, outcome="home_run")
    test_metrics["calibration_k"] = reliability_bins(y_test, probas_test, outcome="strikeout")
    test_metrics["mean_prob_sum"] = float(probas_test.sum(axis=1).mean())

    beats_baseline = better_than_baseline(
        test_metrics["log_loss"],
        baseline_metrics["log_loss"],
    )

    metrics = {
        "model_version": MODEL_VERSION,
        "estimator": type(base).__name__,
        "calibration_method": calibration or "none",
        "compact_features": compact_features,
        "stack_baseline": stack_baseline,
        "class_balanced_weights": class_balanced,
        "feature_count": len(feature_cols),
        "train_end": train_end.isoformat(),
        "val_end": val_end.isoformat(),
        "test_end": test_end.isoformat() if test_end else None,
        "seasons": seasons,
        "test": test_metrics,
        "baseline_on_same_test": baseline_metrics,
        "beats_baseline_log_loss": beats_baseline,
        "split_sizes": {"train": len(train), "val": len(val), "test": len(test)},
    }

    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    bundle = {
        "model": model,
        "feature_columns": feature_cols,
        "outcome_classes": list(OUTCOME_CLASSES),
        "model_version": MODEL_VERSION,
        "compact_features": compact_features,
        "stack_baseline": stack_baseline,
        "baseline_model": baseline_for_stack,
    }
    joblib.dump(bundle, ARTIFACT_PATH)

    xgb_est = model if hasattr(model, "get_booster") else _underlying_xgb_for_export(model)
    if xgb_est is not None:
        json_path = ARTIFACT_PATH.parent / f"{MODEL_VERSION}.xgb.json"
        meta_path = ARTIFACT_PATH.parent / f"{MODEL_VERSION}.meta.joblib"
        xgb_est.save_model(json_path)
        meta = {k: v for k, v in bundle.items() if k != "model"}
        meta["xgb_json"] = json_path.name
        joblib.dump(meta, meta_path)

    ACTIVE_MODEL_FILE.write_text(
        json.dumps(
            {
                "model_version": MODEL_VERSION,
                "artifact": str(ARTIFACT_PATH.name),
                "beats_baseline": beats_baseline,
                "test_log_loss": test_metrics["log_loss"],
                "baseline_log_loss": baseline_metrics["log_loss"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    report_path = settings.data_cache_dir / "reports" / f"model-eval-{MODEL_VERSION}.json"
    report_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    session = create_session(settings.database_url)
    try:
        stmt = insert(ModelEvaluation).values(
            model_version=MODEL_VERSION,
            evaluation_type="xgb_multiclass_calibrated",
            train_start=pd.to_datetime(train["game_date"]).min().date() if len(train) else None,
            train_end=train_end,
            test_start=val_end,
            test_end=test_end or (pd.to_datetime(test["game_date"]).max().date() if len(test) else None),
            metrics=metrics,
        )
        session.execute(stmt)
        session.commit()
    finally:
        session.close()

    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Train advanced PA outcome model")
    parser.add_argument("--seasons", nargs="+", type=int, default=[2021, 2022, 2023, 2024])
    parser.add_argument("--train-end", default="2024-07-31")
    parser.add_argument("--val-end", default="2024-08-31")
    parser.add_argument("--test-end", default="2024-10-31")
    parser.add_argument("--calibration", choices=("sigmoid", "isotonic", "none"), default="sigmoid")
    parser.add_argument("--compact-features", action="store_true", default=True)
    parser.add_argument("--full-features", action="store_true")
    parser.add_argument("--no-stack-baseline", action="store_true")
    parser.add_argument("--no-class-balance", action="store_true")
    args = parser.parse_args()

    cal = None if args.calibration == "none" else args.calibration
    metrics = train_and_evaluate(
        seasons=args.seasons,
        train_end=date.fromisoformat(args.train_end),
        val_end=date.fromisoformat(args.val_end),
        test_end=date.fromisoformat(args.test_end) if args.test_end else None,
        calibration=cal,
        compact_features=not args.full_features,
        stack_baseline=not args.no_stack_baseline,
        class_balanced=not args.no_class_balance,
    )
    test = metrics.get("test", {})
    base = metrics.get("baseline_on_same_test", {})
    logger.info(
        "Test log_loss=%.4f (baseline %.4f) brier=%.4f n=%s beats_baseline=%s",
        test.get("log_loss", float("nan")),
        base.get("log_loss", float("nan")),
        test.get("multiclass_brier", float("nan")),
        test.get("n"),
        metrics.get("beats_baseline_log_loss"),
    )


if __name__ == "__main__":
    main()
