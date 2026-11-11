"""Aggregate PA probabilities to player-game expected counting stats."""

from __future__ import annotations

import numpy as np
import pandas as pd

from data_pipeline.features.constants import OUTCOME_CLASSES


def expected_counting_stats(probas: np.ndarray) -> pd.DataFrame:
    idx = {o: i for i, o in enumerate(OUTCOME_CLASSES)}
    return pd.DataFrame(
        {
            "exp_strikeouts": probas[:, idx["strikeout"]],
            "exp_walks": probas[:, idx["walk"]],
            "exp_hits": probas[:, idx["single"]]
            + probas[:, idx["double"]]
            + probas[:, idx["triple"]]
            + probas[:, idx["home_run"]],
            "exp_home_runs": probas[:, idx["home_run"]],
            "exp_total_bases": probas[:, idx["single"]]
            + 2 * probas[:, idx["double"]]
            + 3 * probas[:, idx["triple"]]
            + 4 * probas[:, idx["home_run"]],
        }
    )


def player_game_mae(frame: pd.DataFrame, probas: np.ndarray) -> dict[str, float]:
    exp = expected_counting_stats(probas)
    work = pd.concat(
        [
            frame[["game_pk", "batter_id", "outcome"]].reset_index(drop=True),
            exp,
        ],
        axis=1,
    )
    hit_mask = work["outcome"].isin(["single", "double", "triple", "home_run"]).astype(float)
    work["act_hits"] = hit_mask
    work["act_k"] = (work["outcome"] == "strikeout").astype(float)
    work["act_bb"] = (work["outcome"] == "walk").astype(float)
    work["act_hr"] = (work["outcome"] == "home_run").astype(float)

    grouped = work.groupby(["game_pk", "batter_id"], as_index=False).agg(
        exp_strikeouts=("exp_strikeouts", "sum"),
        exp_walks=("exp_walks", "sum"),
        exp_hits=("exp_hits", "sum"),
        exp_home_runs=("exp_home_runs", "sum"),
        act_k=("act_k", "sum"),
        act_bb=("act_bb", "sum"),
        act_hits=("act_hits", "sum"),
        act_hr=("act_hr", "sum"),
    )
    if grouped.empty:
        return {}
    return {
        "player_game_k_mae": float((grouped["exp_strikeouts"] - grouped["act_k"]).abs().mean()),
        "player_game_bb_mae": float((grouped["exp_walks"] - grouped["act_bb"]).abs().mean()),
        "player_game_hits_mae": float((grouped["exp_hits"] - grouped["act_hits"]).abs().mean()),
        "player_game_hr_mae": float((grouped["exp_home_runs"] - grouped["act_hr"]).abs().mean()),
        "player_game_n": int(len(grouped)),
    }
