"""Aggregate pitch-level Statcast rows into one row per plate appearance."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from data_pipeline.transform.outcomes import classify_event

REQUIRED_COLUMNS = {
    "game_pk",
    "at_bat_number",
    "pitch_number",
    "batter",
    "pitcher",
    "game_date",
    "home_team",
    "away_team",
}


def _normalize_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "game_date" in out.columns:
        out["game_date"] = pd.to_datetime(out["game_date"]).dt.date
    for col in ("game_pk", "at_bat_number", "pitch_number", "batter", "pitcher"):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").astype("Int64")
    return out


def pitches_to_plate_appearances(
    pitches: pd.DataFrame,
    *,
    retrieved_at: datetime | None = None,
) -> pd.DataFrame:
    """
    Build plate-appearance records from pitch-level Statcast.

    Uses the terminal pitch (max pitch_number per at-bat) for event classification.
    """
    missing = REQUIRED_COLUMNS - set(pitches.columns)
    if missing:
        raise ValueError(f"Statcast frame missing columns: {sorted(missing)}")

    df = _normalize_dtypes(pitches)
    df = df.dropna(subset=["game_pk", "at_bat_number", "pitch_number", "batter", "pitcher"])

    sort_cols = ["game_pk", "at_bat_number", "pitch_number"]
    df = df.sort_values(sort_cols)

    idx = df.groupby(["game_pk", "at_bat_number"])["pitch_number"].idxmax()
    terminal = df.loc[idx].copy()

    pitch_counts = (
        df.groupby(["game_pk", "at_bat_number"])
        .size()
        .reset_index(name="pitches_in_pa")
    )
    terminal = terminal.merge(pitch_counts, on=["game_pk", "at_bat_number"])

    events = terminal.get("events")
    if events is not None:
        terminal["outcome"] = events.map(classify_event)
    else:
        terminal["outcome"] = classify_event(None)

    # Statcast `player_name` is the pitcher on pitch rows, not the batter — do not map to batter_name.
    terminal["batter_name"] = None

    if "pitcher_name" in terminal.columns:
        terminal["pitcher_name_col"] = terminal["pitcher_name"]
    elif "player_name" in terminal.columns:
        terminal["pitcher_name_col"] = terminal["player_name"]
    else:
        terminal["pitcher_name_col"] = None

    if retrieved_at is None:
        retrieved_at = datetime.now(timezone.utc)
    terminal["source_retrieved_at"] = retrieved_at

    keep = [
        "game_pk",
        "at_bat_number",
        "batter",
        "pitcher",
        "game_date",
        "inning",
        "inning_topbot",
        "outs_when_up",
        "home_team",
        "away_team",
        "events",
        "description",
        "stand",
        "p_throws",
        "venue_id",
        "venue_name",
        "pitches_in_pa",
        "outcome",
        "batter_name",
        "pitcher_name_col",
        "source_retrieved_at",
    ]
    present = [c for c in keep if c in terminal.columns]
    return terminal[present].reset_index(drop=True)
