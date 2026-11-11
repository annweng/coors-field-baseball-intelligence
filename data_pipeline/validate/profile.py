"""Extended dataset profiling beyond core quality gates."""

from __future__ import annotations

from typing import Any

import pandas as pd

from data_pipeline.transform.outcomes import classify_event, VALID_OUTCOMES
from data_pipeline.transform.plate_appearances import pitches_to_plate_appearances
from data_pipeline.validate.quality import build_quality_report


def build_season_profile(
    pitches: pd.DataFrame,
    *,
    season: int,
    in_database: bool | None = None,
) -> dict[str, Any]:
    """Merge quality checks with descriptive coverage statistics."""
    pa = pitches_to_plate_appearances(pitches)
    report = build_quality_report(pitches, pa, season=season)

    if not pa.empty:
        dates = pd.to_datetime(pa["game_date"])
        report["date_range"] = {
            "min": dates.min().date().isoformat(),
            "max": dates.max().date().isoformat(),
        }
        report["unique_games"] = int(pa["game_pk"].nunique())
        report["unique_batters"] = int(pa["batter"].nunique())
        report["unique_pitchers"] = int(pa["pitcher"].nunique())

        if "venue_id" in pa.columns:
            report["unique_stadiums"] = int(pa["venue_id"].nunique())
            coors_ids = {19, 3312}
            coors_mask = pa["venue_id"].isin(coors_ids)
            report["coors_field_plate_appearances"] = int(coors_mask.sum())

        if "events" in pa.columns:
            raw_events = pa["events"].dropna().astype(str).str.lower().unique().tolist()
            mapped = {e: classify_event(e) for e in raw_events}
            unmapped_other = [e for e, o in mapped.items() if o == "other_out" and e not in VALID_OUTCOMES]
            report["distinct_raw_events"] = int(len(raw_events))
            report["sample_unmapped_events"] = sorted(unmapped_other)[:25]

    if in_database is not None:
        report["loaded_in_postgres"] = in_database
    report["data_source"] = "statcast_pybaseball"
    return report


def merge_profiles(profiles: list[dict[str, Any]]) -> dict[str, Any]:
    seasons = sorted({p["season"] for p in profiles if p.get("season") is not None})
    total_pa = sum(int(p.get("plate_appearances", 0)) for p in profiles)
    total_pitches = sum(int(p.get("pitch_rows", 0)) for p in profiles)
    by_season = {str(p["season"]): p for p in profiles}
    return {
        "seasons": seasons,
        "season_profiles": by_season,
        "aggregate_pitch_rows": total_pitches,
        "aggregate_plate_appearances": total_pa,
        "all_quality_passed": all(p.get("passed") for p in profiles if "passed" in p),
    }
