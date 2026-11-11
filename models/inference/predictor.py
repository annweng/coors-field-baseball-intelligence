"""Load trained artifact and predict PA outcome probabilities."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from data_pipeline.features.constants import OUTCOME_CLASSES, COORS_FIELD_STADIUM_IDS
from data_pipeline.features.cache import load_or_build_features
from data_pipeline.load.reader import load_plate_appearances_frame
from data_pipeline.settings import settings
from models.advanced.feature_matrix import append_baseline_probas, encode_matrix

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACT = ROOT / "models" / "artifacts" / "xgb-v0.2.2.joblib"
FALLBACK_ARTIFACT = ROOT / "models" / "artifacts" / "gbm-v0.1.0.joblib"


def _resolve_artifact(path: Path | None = None) -> Path:
    if path and path.exists():
        return path
    if DEFAULT_ARTIFACT.exists():
        return DEFAULT_ARTIFACT
    if FALLBACK_ARTIFACT.exists():
        return FALLBACK_ARTIFACT
    raise FileNotFoundError("No model artifact found. Run models.train_advanced first.")


class PaOutcomePredictor:
    def __init__(self, artifact_path: Path | None = None) -> None:
        path = _resolve_artifact(artifact_path)
        bundle = joblib.load(path)
        self.model = bundle["model"]
        self.feature_columns: list[str] = bundle["feature_columns"]
        self.outcome_classes: list[str] = bundle.get("outcome_classes", list(OUTCOME_CLASSES))
        self.model_version: str = bundle.get("model_version", path.stem)
        self.compact_features: bool = bundle.get("compact_features", True)
        self.baseline_model = bundle.get("baseline_model")

    def predict_from_frame(self, frame: pd.DataFrame) -> np.ndarray:
        work = frame.copy()
        if self.baseline_model is not None:
            work = append_baseline_probas(work, self.baseline_model)
        x, _ = encode_matrix(work, compact=self.compact_features)
        for col in self.feature_columns:
            if col not in x.columns:
                x[col] = 0.0
        x = x[self.feature_columns]
        probas = self.model.predict_proba(x)
        classes = list(self.model.classes_)
        order = [classes.index(c) for c in OUTCOME_CLASSES if c in classes]
        ordered = probas[:, order]
        return ordered / ordered.sum(axis=1, keepdims=True)

    def predict_matchup(
        self,
        *,
        batter_id: int,
        pitcher_id: int,
        stadium_id: int | None,
        as_of_season: int = 2024,
    ) -> dict[str, float]:
        """Use latest rolling features for batter/pitcher before inferring a hypothetical PA."""
        raw = load_plate_appearances_frame(settings.database_url, seasons=[as_of_season])
        raw = raw[raw["outcome"] != "unknown"]
        featured = load_or_build_features(raw, season=as_of_season)

        b_rows = featured[featured["batter_id"] == batter_id]
        p_rows = featured[featured["pitcher_id"] == pitcher_id]
        if b_rows.empty or p_rows.empty:
            raise ValueError("Insufficient history for batter or pitcher in selected season")

        template = b_rows.sort_values("game_date").iloc[-1].copy()
        p_latest = p_rows.sort_values("game_date").iloc[-1]

        for col in featured.columns:
            if col.startswith("pitch_"):
                template[col] = p_latest[col]

        template["pitcher_id"] = pitcher_id
        if stadium_id is not None:
            template["stadium_id"] = stadium_id
            template["is_coors"] = int(stadium_id in COORS_FIELD_STADIUM_IDS)

        probas = self.predict_from_frame(pd.DataFrame([template]))[0]
        return {
            OUTCOME_CLASSES[i]: float(probas[i])
            for i in range(len(OUTCOME_CLASSES))
        }
