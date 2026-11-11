"""Leakage-safe rolling batter and pitcher features."""

from __future__ import annotations

import numpy as np
import pandas as pd

from data_pipeline.features.constants import COORS_FIELD_STADIUM_IDS, OUTCOME_CLASSES, WOBA_WEIGHTS


def _prepare_outcome_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["game_date"] = pd.to_datetime(out["game_date"])
    for outcome in OUTCOME_CLASSES:
        out[f"is_{outcome}"] = (out["outcome"] == outcome).astype(np.int8)
    out["woba_numerator"] = sum(
        out[f"is_{o}"] * WOBA_WEIGHTS[o] for o in OUTCOME_CLASSES
    )
    if "season" not in out.columns:
        out["season"] = out["game_date"].dt.year
        out.loc[out["game_date"].dt.month < 3, "season"] -= 1
    return out


def _rolling_rates_for_player(group: pd.DataFrame, prefix: str) -> pd.DataFrame:
    """
    Calendar-window and season-to-date rates for one player's PA sequence.

    shift(1) on all cumulative/rolling totals excludes the current plate appearance.
    """
    group = group.sort_values(["game_date", "game_pk", "at_bat_number"])
    indexed = group.set_index("game_date")
    features = pd.DataFrame(index=indexed.index)
    features["game_pk"] = indexed["game_pk"].values
    features["at_bat_number"] = indexed["at_bat_number"].values

    ones = pd.Series(1, index=indexed.index, dtype=float)

    for days in (7, 30, 60):
        prior_pa = ones.rolling(f"{days}D").sum().shift(1)
        features[f"{prefix}_pa_{days}d"] = prior_pa
        for outcome in OUTCOME_CLASSES:
            hits = indexed[f"is_{outcome}"].rolling(f"{days}D").sum().shift(1)
            features[f"{prefix}_{outcome}_rate_{days}d"] = hits / prior_pa.replace(0, np.nan)
        wsum = indexed["woba_numerator"].rolling(f"{days}D").sum().shift(1)
        features[f"{prefix}_woba_{days}d"] = wsum / prior_pa.replace(0, np.nan)

    reset = indexed.reset_index()
    reset["_row"] = np.arange(len(reset))
    # cumcount() = number of prior PAs in the season (0 for the first PA).
    prior_pa_st = reset.groupby("season", sort=False).cumcount()
    features[f"{prefix}_pa_season"] = prior_pa_st.values

    for outcome in OUTCOME_CLASSES:
        csum = reset.groupby("season", sort=False)[f"is_{outcome}"].cumsum().shift(1).fillna(0)
        features[f"{prefix}_{outcome}_rate_season"] = csum.values / prior_pa_st.replace(0, np.nan)

    woba_csum = reset.groupby("season", sort=False)["woba_numerator"].cumsum().shift(1).fillna(0)
    features[f"{prefix}_woba_season"] = woba_csum.values / prior_pa_st.replace(0, np.nan)

    return features.reset_index()


def build_rolling_features(plate_appearances: pd.DataFrame) -> pd.DataFrame:
    """Attach batter (batt_) and pitcher (pitch_) rolling feature columns."""
    base = _prepare_outcome_columns(plate_appearances)

    batter_frames: list[pd.DataFrame] = []
    for _, grp in base.groupby("batter_id", sort=False):
        feat = _rolling_rates_for_player(grp, "batt")
        batter_frames.append(feat)

    pitcher_frames: list[pd.DataFrame] = []
    for _, grp in base.groupby("pitcher_id", sort=False):
        feat = _rolling_rates_for_player(grp, "pitch")
        pitcher_frames.append(feat)

    batter_feat = pd.concat(batter_frames, ignore_index=True)
    pitcher_feat = pd.concat(pitcher_frames, ignore_index=True)
    merge_keys = ["game_date", "game_pk", "at_bat_number"]

    batter_cols = merge_keys + [c for c in batter_feat.columns if c.startswith("batt_")]
    pitcher_cols = merge_keys + [c for c in pitcher_feat.columns if c.startswith("pitch_")]

    merged = base.merge(batter_feat[batter_cols], on=merge_keys, how="left")
    merged = merged.merge(pitcher_feat[pitcher_cols], on=merge_keys, how="left")

    if "stadium_id" in merged.columns:
        merged["is_coors"] = merged["stadium_id"].isin(COORS_FIELD_STADIUM_IDS).astype(int)
    else:
        merged["is_coors"] = 0

    return merged


def minimum_prior_plate_appearances(df: pd.DataFrame, *, min_pa: int = 5) -> pd.Series:
    """True when batter and pitcher each have at least ``min_pa`` prior PAs (30d window)."""
    b_pa = df.get("batt_pa_30d", pd.Series(0, index=df.index)).fillna(0)
    p_pa = df.get("pitch_pa_30d", pd.Series(0, index=df.index)).fillna(0)
    return (b_pa >= min_pa) & (p_pa >= min_pa)
