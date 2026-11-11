"""Baseline forecaster inference for live API."""

from __future__ import annotations

from datetime import date

import pandas as pd

from data_pipeline.features.cache import load_or_build_features
from data_pipeline.features.constants import COORS_FIELD_STADIUM_IDS, OUTCOME_CLASSES
from data_pipeline.features.rolling import minimum_prior_plate_appearances
from data_pipeline.load.reader import load_plate_appearances_frame
from data_pipeline.settings import settings
from models.baseline.forecaster import BaselineForecaster
from models.evaluation.splits import chronological_split


def baseline_matchup_probabilities(
    *,
    batter_id: int,
    pitcher_id: int,
    stadium_id: int | None,
    as_of_season: int = 2024,
) -> dict[str, float]:
    raw = load_plate_appearances_frame(settings.database_url, seasons=[as_of_season])
    raw = raw[raw["outcome"] != "unknown"]
    featured = load_or_build_features(raw, season=as_of_season)
    eligible = featured[minimum_prior_plate_appearances(featured, min_pa=5)]

    train_end = date(as_of_season, 7, 31)
    val_end = date(as_of_season, 8, 31)
    train, _, _ = chronological_split(eligible, train_end=train_end, val_end=val_end)

    model = BaselineForecaster()
    model.fit(train)

    b_rows = featured[featured["batter_id"] == batter_id]
    p_rows = featured[featured["pitcher_id"] == pitcher_id]
    if b_rows.empty or p_rows.empty:
        raise ValueError("Insufficient history for batter or pitcher in selected season")

    row = b_rows.sort_values("game_date").iloc[-1].copy()
    p_last = p_rows.sort_values("game_date").iloc[-1]
    for col in featured.columns:
        if col.startswith("pitch_"):
            row[col] = p_last[col]
    row["pitcher_id"] = pitcher_id
    if stadium_id is not None:
        row["stadium_id"] = stadium_id
        row["is_coors"] = int(stadium_id in COORS_FIELD_STADIUM_IDS)

    probas = model.predict_proba(pd.DataFrame([row]))[0]
    return {OUTCOME_CLASSES[i]: float(probas[i]) for i in range(len(OUTCOME_CLASSES))}
