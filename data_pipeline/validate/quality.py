"""Data quality checks for plate-appearance datasets."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd

from data_pipeline.transform.outcomes import VALID_OUTCOMES


def build_quality_report(
    pitches: pd.DataFrame,
    plate_appearances: pd.DataFrame,
    *,
    season: int | None = None,
) -> dict[str, Any]:
    """Produce a concise JSON-serializable quality report."""
    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "season": season,
        "pitch_rows": int(len(pitches)),
        "plate_appearances": int(len(plate_appearances)),
    }

    if pitches.empty:
        report["errors"] = ["empty_pitch_dataset"]
        return report

    dup_keys = pitches.duplicated(subset=["game_pk", "at_bat_number", "pitch_number"], keep=False)
    report["duplicate_pitches"] = int(dup_keys.sum())

    missing_batter = int(pitches["batter"].isna().sum()) if "batter" in pitches.columns else 0
    missing_pitcher = int(pitches["pitcher"].isna().sum()) if "pitcher" in pitches.columns else 0
    report["missing_batter_id"] = missing_batter
    report["missing_pitcher_id"] = missing_pitcher

    if "game_date" in pitches.columns:
        invalid_dates = pitches["game_date"].isna().sum()
        report["invalid_game_dates"] = int(invalid_dates)

    if not plate_appearances.empty:
        pa_dup = plate_appearances.duplicated(subset=["game_pk", "at_bat_number"]).sum()
        report["duplicate_plate_appearances"] = int(pa_dup)

        unknown_outcomes = int((~plate_appearances["outcome"].isin(VALID_OUTCOMES)).sum())
        report["invalid_outcome_labels"] = unknown_outcomes
        report["unknown_outcome_count"] = int((plate_appearances["outcome"] == "unknown").sum())
        report["outcome_distribution"] = (
            plate_appearances["outcome"].value_counts().sort_index().to_dict()
        )

        missing_stadium = 0
        if "venue_id" in plate_appearances.columns:
            missing_stadium = int(plate_appearances["venue_id"].isna().sum())
        report["missing_stadium_id"] = missing_stadium

    report["passed"] = (
        report.get("duplicate_plate_appearances", 0) == 0
        and report.get("invalid_outcome_labels", 0) == 0
        and missing_batter == 0
        and missing_pitcher == 0
    )
    return report
