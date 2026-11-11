"""Train team-level runs model with chronological holdout."""

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
from sklearn.linear_model import Ridge

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from data_pipeline.runs.team_games import build_team_game_dataset
from data_pipeline.settings import settings
from models.evaluation.splits import chronological_split
from models.runs.baseline import RunsBaseline
from models.runs.features import encode_matrix

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("train_runs")

MODEL_VERSION = "runs-v0.1.0"
ARTIFACT_PATH = ROOT / "models" / "artifacts" / f"{MODEL_VERSION}.joblib"
ACTIVE_RUNS_FILE = ROOT / "models" / "artifacts" / "active_runs_model.json"


def _mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))


def _rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def better_than_baseline(adv: float, base: float, *, margin: float = 0.05) -> bool:
    return adv < base - margin


def train_and_evaluate(
    *,
    seasons: list[int],
    train_end: date,
    val_end: date,
    test_end: date | None,
) -> dict:
    featured = build_team_game_dataset(seasons=seasons)
    eligible = featured.copy()
    train, val, test = chronological_split(
        eligible,
        train_end=train_end,
        val_end=val_end,
        test_end=test_end,
    )
    logger.info("Splits train/val/test: %s / %s / %s", len(train), len(val), len(test))
    if test.empty:
        raise RuntimeError("Test split empty")

    baseline = RunsBaseline()
    baseline.fit(train)
    y_test = test["runs_scored"].to_numpy(dtype=float)
    base_pred = baseline.predict(test)
    base_mae = _mae(y_test, base_pred)

    x_train, cols = encode_matrix(train)
    x_test, _ = encode_matrix(test)
    y_train = train["runs_scored"].to_numpy(dtype=float)

    ridge = Ridge(alpha=3.0, random_state=42)
    ridge.fit(x_train, y_train)
    test_pred = np.maximum(0.5, ridge.predict(x_test))
    test_mae = _mae(y_test, test_pred)
    test_rmse = _rmse(y_test, test_pred)

    beats = better_than_baseline(test_mae, base_mae)

    metrics = {
        "model_version": MODEL_VERSION,
        "estimator": "Ridge",
        "train_end": train_end.isoformat(),
        "val_end": val_end.isoformat(),
        "test_end": test_end.isoformat() if test_end else None,
        "seasons": seasons,
        "test_mae": test_mae,
        "test_rmse": test_rmse,
        "baseline_test_mae": base_mae,
        "beats_baseline_mae": beats,
        "split_sizes": {"train": len(train), "val": len(val), "test": len(test)},
    }

    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": ridge,
            "feature_columns": cols,
            "baseline": baseline,
            "model_version": MODEL_VERSION,
        },
        ARTIFACT_PATH,
    )
    ACTIVE_RUNS_FILE.write_text(
        json.dumps(
            {
                "model_version": MODEL_VERSION,
                "artifact": ARTIFACT_PATH.name,
                "beats_baseline": beats,
                "test_mae": test_mae,
                "baseline_mae": base_mae,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    report_path = settings.data_cache_dir / "reports" / f"model-eval-{MODEL_VERSION}.json"
    report_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Train team runs model")
    parser.add_argument("--seasons", nargs="+", type=int, default=[2021, 2022, 2023, 2024])
    parser.add_argument("--train-end", default="2024-07-31")
    parser.add_argument("--val-end", default="2024-08-31")
    parser.add_argument("--test-end", default="2024-10-31")
    args = parser.parse_args()
    metrics = train_and_evaluate(
        seasons=args.seasons,
        train_end=date.fromisoformat(args.train_end),
        val_end=date.fromisoformat(args.val_end),
        test_end=date.fromisoformat(args.test_end),
    )
    logger.info(
        "Test MAE=%.3f (baseline %.3f) beats_baseline=%s",
        metrics["test_mae"],
        metrics["baseline_test_mae"],
        metrics["beats_baseline_mae"],
    )


if __name__ == "__main__":
    main()
