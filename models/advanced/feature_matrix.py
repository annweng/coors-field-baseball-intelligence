"""Model-ready feature matrix from rolling PA frame."""

from __future__ import annotations

import pandas as pd

from data_pipeline.features.constants import OUTCOME_CLASSES

BASELINE_PROB_PREFIX = "base_p_"


def feature_columns(frame: pd.DataFrame, *, compact: bool = False) -> list[str]:
    cols: list[str] = []
    for c in frame.columns:
        if not c.startswith(("batt_", "pitch_")):
            continue
        if compact:
            if "_rate_30d" in c or c.endswith("_pa_30d") or "_woba_30d" in c:
                cols.append(c)
            continue
        if (
            "_rate_" in c
            or "_woba_" in c
            or c.endswith("_pa_7d")
            or c.endswith("_pa_30d")
            or c.endswith("_pa_60d")
            or c.endswith("_pa_season")
        ):
            cols.append(c)
    cols.append("is_coors")
    for outcome in OUTCOME_CLASSES:
        col = f"{BASELINE_PROB_PREFIX}{outcome}"
        if col in frame.columns:
            cols.append(col)
    return sorted(set(cols))


def append_baseline_probas(frame: pd.DataFrame, baseline) -> pd.DataFrame:
    """Add baseline model probabilities as columns (stacking features)."""
    work = frame.copy()
    probas = baseline.predict_proba(work)
    for i, outcome in enumerate(OUTCOME_CLASSES):
        work[f"{BASELINE_PROB_PREFIX}{outcome}"] = probas[:, i]
    return work


def encode_matrix(frame: pd.DataFrame, *, compact: bool = False) -> tuple[pd.DataFrame, list[str]]:
    work = frame.copy()
    for side in ("L", "R", "S"):
        work[f"batter_stands_{side}"] = (work["batter_stands"] == side).astype(int)
    for side in ("L", "R"):
        work[f"pitcher_throws_{side}"] = (work["pitcher_throws"] == side).astype(int)

    cols = feature_columns(work, compact=compact) + [
        "batter_stands_L",
        "batter_stands_R",
        "batter_stands_S",
        "pitcher_throws_L",
        "pitcher_throws_R",
    ]
    cols = sorted(set(cols))
    present = [c for c in cols if c in work.columns]
    x = work[present].astype(float).fillna(0.0)
    return x, present
