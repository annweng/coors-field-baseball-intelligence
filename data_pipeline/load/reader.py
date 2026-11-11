"""Read analytical tables from PostgreSQL."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import create_engine, text


def load_plate_appearances_frame(database_url: str, *, seasons: list[int] | None = None) -> pd.DataFrame:
    season_filter = ""
    params: dict = {}
    if seasons:
        season_filter = "AND g.season = ANY(:seasons)"
        params["seasons"] = seasons

    sql = text(
        f"""
        SELECT
            pa.game_pk,
            pa.at_bat_number,
            pa.batter_id,
            pa.pitcher_id,
            pa.game_date,
            g.season,
            pa.home_team_id,
            pa.away_team_id,
            pa.stadium_id,
            pa.batter_stands,
            pa.pitcher_throws,
            pa.outcome::text AS outcome,
            pa.pitches_in_pa
        FROM plate_appearances pa
        JOIN games g ON g.game_pk = pa.game_pk
        WHERE pa.outcome IS NOT NULL
        {season_filter}
        ORDER BY pa.game_date, pa.game_pk, pa.at_bat_number
        """
    )
    engine = create_engine(database_url, pool_pre_ping=True)
    with engine.connect() as conn:
        return pd.read_sql(sql, conn, params=params)
