"""Team-game rows with rolling offense/defense features (pre-game only)."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import create_engine, text

from data_pipeline.features.constants import COORS_FIELD_STADIUM_IDS
from data_pipeline.settings import settings


def _load_scored_games(database_url: str, seasons: list[int]) -> pd.DataFrame:
    engine = create_engine(database_url)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT g.game_pk, g.game_date, g.season, g.stadium_id,
                       g.home_team_id, g.away_team_id, g.home_score, g.away_score
                FROM games g
                WHERE g.season = ANY(:seasons)
                  AND g.home_score IS NOT NULL
                  AND g.away_score IS NOT NULL
                ORDER BY g.game_date, g.game_pk
                """
            ),
            {"seasons": seasons},
        ).mappings().all()
    if not rows:
        return pd.DataFrame()
    games = pd.DataFrame(rows)
    games["game_date"] = pd.to_datetime(games["game_date"])
    return games


def _team_long(games: pd.DataFrame) -> pd.DataFrame:
    home = games.rename(
        columns={
            "home_team_id": "team_id",
            "away_team_id": "opponent_id",
            "home_score": "runs_scored",
            "away_score": "runs_allowed",
        }
    )
    home["is_home"] = 1
    away = games.rename(
        columns={
            "away_team_id": "team_id",
            "home_team_id": "opponent_id",
            "away_score": "runs_scored",
            "home_score": "runs_allowed",
        }
    )
    away["is_home"] = 0
    cols = [
        "game_pk",
        "game_date",
        "season",
        "stadium_id",
        "team_id",
        "opponent_id",
        "is_home",
        "runs_scored",
        "runs_allowed",
    ]
    return pd.concat([home[cols], away[cols]], ignore_index=True)


def _rolling_team_stats(long: pd.DataFrame, window_days: int = 30) -> pd.DataFrame:
    work = long.sort_values(["team_id", "game_date", "game_pk"]).copy()
    work["is_coors"] = work["stadium_id"].isin(COORS_FIELD_STADIUM_IDS).astype(int)

    pieces: list[pd.DataFrame] = []
    for _, grp in work.groupby("team_id", sort=False):
        g = grp.sort_values("game_date").set_index("game_date")
        chunk = grp.sort_values("game_date").copy()
        chunk[f"team_rs_{window_days}d"] = (
            g["runs_scored"].rolling(f"{window_days}D", closed="left").mean().to_numpy()
        )
        chunk[f"team_ra_{window_days}d"] = (
            g["runs_allowed"].rolling(f"{window_days}D", closed="left").mean().to_numpy()
        )
        pieces.append(chunk)
    work = pd.concat(pieces, ignore_index=True)

    work["team_rs_season"] = (
        work.groupby(["team_id", "season"])["runs_scored"]
        .transform(lambda s: s.expanding().mean().shift(1))
    )
    work["team_ra_season"] = (
        work.groupby(["team_id", "season"])["runs_allowed"]
        .transform(lambda s: s.expanding().mean().shift(1))
    )

    opp = work[["game_pk", "team_id", f"team_rs_{window_days}d", f"team_ra_{window_days}d"]].rename(
        columns={
            "team_id": "opponent_id",
            f"team_rs_{window_days}d": f"opp_rs_{window_days}d",
            f"team_ra_{window_days}d": f"opp_ra_{window_days}d",
        }
    )
    work = work.merge(opp, on=["game_pk", "opponent_id"], how="left")
    return work


def build_team_game_dataset(
    *,
    database_url: str | None = None,
    seasons: list[int] | None = None,
) -> pd.DataFrame:
    database_url = database_url or settings.database_url
    seasons = seasons or [2021, 2022, 2023, 2024]
    games = _load_scored_games(database_url, seasons)
    if games.empty:
        raise RuntimeError("No scored games in database — run: python -m data_pipeline.cli sync-scores")
    long = _team_long(games)
    featured = _rolling_team_stats(long)
    featured = featured[
        featured["team_rs_30d"].notna()
        & featured["team_ra_30d"].notna()
        & featured["team_rs_season"].notna()
        & featured[f"opp_rs_30d"].notna()
    ].copy()
    return featured
