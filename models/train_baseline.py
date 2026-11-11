"""Train and evaluate the baseline plate-appearance model."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from data_pipeline.features.constants import OUTCOME_CLASSES
from data_pipeline.features.rolling import build_rolling_features, minimum_prior_plate_appearances
from data_pipeline.load.postgres import create_session
from data_pipeline.load.reader import load_plate_appearances_frame
from data_pipeline.settings import settings
from models.baseline.forecaster import BaselineForecaster
from models.evaluation.metrics import evaluate_multiclass
from models.evaluation.splits import chronological_split

from app.db.models import ModelEvaluation
from sqlalchemy.dialects.postgresql import insert

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("train_baseline")

MODEL_VERSION = "baseline-v0.1.0"


def train_and_evaluate(
    *,
    train_end: date,
    val_end: date,
    seasons: list[int] | None = None,
) -> dict:
    raw = load_plate_appearances_frame(settings.database_url, seasons=seasons)
    raw = raw[raw["outcome"] != "unknown"].copy()
    logger.info("Loaded %s plate appearances from database", len(raw))

    featured = build_rolling_features(raw)
    eligible = featured[minimum_prior_plate_appearances(featured, min_pa=5)].copy()
    logger.info("Eligible rows after min prior PA filter: %s", len(eligible))

    train, val, test = chronological_split(eligible, train_end=train_end, val_end=val_end)
    logger.info("Split sizes train/val/test: %s / %s / %s", len(train), len(val), len(test))

    model = BaselineForecaster()
    model.fit(train)

    def _eval_split(name: str, frame: pd.DataFrame) -> dict:
        if frame.empty:
            return {"n": 0}
        probas = model.predict_proba(frame)
        stats = evaluate_multiclass(frame["outcome"].tolist(), probas)
        stats["split"] = name
        return stats

    metrics = {
        "model_version": MODEL_VERSION,
        "train": _eval_split("train", train),
        "validation": _eval_split("validation", val),
        "test": _eval_split("test", test),
        "split_dates": {
            "train_end": train_end.isoformat(),
            "val_end": val_end.isoformat(),
        },
        "seasons": seasons,
        "features": [
            "batt_*_rate_30d",
            "pitch_*_rate_30d",
            "batt_*_rate_season (fallback)",
            "league smoothed blend",
        ],
    }

    out_path = settings.data_cache_dir / "reports" / f"model-eval-{MODEL_VERSION}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    logger.info("Wrote %s", out_path)

    session = create_session(settings.database_url)
    try:
        stmt = insert(ModelEvaluation).values(
            model_version=MODEL_VERSION,
            evaluation_type="baseline_multiclass",
            train_start=pd.to_datetime(train["game_date"]).min().date() if len(train) else None,
            train_end=train_end,
            test_start=val_end,
            test_end=pd.to_datetime(test["game_date"]).max().date() if len(test) else None,
            metrics=metrics,
        )
        session.execute(stmt)
        session.commit()
    finally:
        session.close()

    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Train baseline PA outcome model")
    parser.add_argument("--train-end", default="2024-07-31", help="Last date included in training")
    parser.add_argument("--val-end", default="2024-08-31", help="Last date included in validation")
    parser.add_argument("--seasons", nargs="*", type=int, default=None)
    args = parser.parse_args()

    metrics = train_and_evaluate(
        train_end=date.fromisoformat(args.train_end),
        val_end=date.fromisoformat(args.val_end),
        seasons=args.seasons,
    )
    test = metrics.get("test", {})
    logger.info(
        "Test log_loss=%.4f brier=%.4f n=%s",
        test.get("log_loss", float("nan")),
        test.get("multiclass_brier", float("nan")),
        test.get("n"),
    )


if __name__ == "__main__":
    main()
