"""Coors Field and park-effect analytics (descriptive)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

ROCKIES_TEAM_ID = 115

OUTCOME_RATE_SQL = """
    AVG(CASE WHEN pa.outcome::text = 'strikeout' THEN 1.0 ELSE 0.0 END) AS k_rate,
    AVG(CASE WHEN pa.outcome::text = 'walk' THEN 1.0 ELSE 0.0 END) AS bb_rate,
    AVG(CASE WHEN pa.outcome::text = 'home_run' THEN 1.0 ELSE 0.0 END) AS hr_rate,
    AVG(CASE WHEN pa.outcome::text IN ('single','double','triple','home_run') THEN 1.0 ELSE 0.0 END) AS hit_rate,
    AVG(CASE WHEN pa.outcome::text = 'single' THEN 1.0 ELSE 0.0 END) AS single_rate,
    AVG(CASE WHEN pa.outcome::text = 'double' THEN 1.0 ELSE 0.0 END) AS double_rate,
    AVG(CASE WHEN pa.outcome::text = 'triple' THEN 1.0 ELSE 0.0 END) AS triple_rate,
    COUNT(*) AS pa
"""


def _season_filter(season: int | None) -> tuple[str, dict[str, Any]]:
    if season is None:
        return "", {}
    return "AND g.season = :season", {"season": season}


def park_comparison(conn: Connection, season: int | None = None) -> dict[str, Any]:
    where, params = _season_filter(season)
    coors = conn.execute(
        text(
            f"""
            SELECT 'coors' AS site, {OUTCOME_RATE_SQL}
            FROM plate_appearances pa
            JOIN games g ON g.game_pk = pa.game_pk
            JOIN stadiums s ON s.stadium_id = pa.stadium_id
            WHERE s.is_coors_field = TRUE AND pa.outcome::text != 'unknown' {where}
            """
        ),
        params,
    ).mappings().first()

    league = conn.execute(
        text(
            f"""
            SELECT 'league' AS site, {OUTCOME_RATE_SQL}
            FROM plate_appearances pa
            JOIN games g ON g.game_pk = pa.game_pk
            WHERE pa.outcome::text != 'unknown' {where}
            """
        ),
        params,
    ).mappings().first()

    return {
        "season": season,
        "coors_field": dict(coors) if coors else {},
        "league_average": dict(league) if league else {},
        "note": "Descriptive rates per plate appearance; not a causal altitude estimate.",
    }


def coors_league_index(conn: Connection, season: int | None = None) -> dict[str, float]:
    comp = park_comparison(conn, season)
    c, L = comp.get("coors_field", {}), comp.get("league_average", {})
    if not c.get("pa") or not L.get("pa"):
        return {}
    return {
        "hr_index": float(c["hr_rate"]) / float(L["hr_rate"]) if L.get("hr_rate") else 0,
        "hit_index": float(c["hit_rate"]) / float(L["hit_rate"]) if L.get("hit_rate") else 0,
        "k_index": float(c["k_rate"]) / float(L["k_rate"]) if L.get("k_rate") else 0,
    }


def rockies_offense_splits(conn: Connection, season: int | None = None) -> dict[str, Any]:
    """Rockies batting PAs: at Coors vs all other venues."""
    where, params = _season_filter(season)
    rows = conn.execute(
        text(
            f"""
            SELECT
              CASE WHEN s.is_coors_field THEN 'at_coors' ELSE 'away_from_coors' END AS split,
              {OUTCOME_RATE_SQL}
            FROM plate_appearances pa
            JOIN games g ON g.game_pk = pa.game_pk
            LEFT JOIN stadiums s ON s.stadium_id = pa.stadium_id
            WHERE pa.outcome::text != 'unknown'
              AND (
                (g.home_team_id = :team_id AND UPPER(pa.inning_topbot) = 'BOT')
                OR (g.away_team_id = :team_id AND UPPER(pa.inning_topbot) = 'TOP')
              )
              {where}
            GROUP BY 1
            """
        ),
        {**params, "team_id": ROCKIES_TEAM_ID},
    ).mappings().all()
    return {
        "season": season,
        "team_id": ROCKIES_TEAM_ID,
        "team_name": "Colorado Rockies",
        "splits": [dict(r) for r in rows],
        "note": "Rockies batting only; descriptive split.",
    }


def seasonal_trend_at_coors(conn: Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        text(
            f"""
            SELECT g.season,
              {OUTCOME_RATE_SQL}
            FROM plate_appearances pa
            JOIN games g ON g.game_pk = pa.game_pk
            JOIN stadiums s ON s.stadium_id = pa.stadium_id
            WHERE s.is_coors_field = TRUE AND pa.outcome::text != 'unknown'
            GROUP BY g.season
            ORDER BY g.season
            """
        )
    ).mappings().all()
    return [dict(r) for r in rows]


def top_stadiums_by_hr_rate(conn: Connection, season: int | None = None, limit: int = 10) -> list[dict[str, Any]]:
    where, params = _season_filter(season)
    rows = conn.execute(
        text(
            f"""
            SELECT s.name, s.stadium_id, s.is_coors_field,
              {OUTCOME_RATE_SQL}
            FROM plate_appearances pa
            JOIN games g ON g.game_pk = pa.game_pk
            JOIN stadiums s ON s.stadium_id = pa.stadium_id
            WHERE pa.outcome::text != 'unknown' {where}
            GROUP BY s.stadium_id, s.name, s.is_coors_field
            HAVING COUNT(*) >= 500
            ORDER BY hr_rate DESC
            LIMIT :lim
            """
        ),
        {**params, "lim": limit},
    ).mappings().all()
    return [dict(r) for r in rows]


def summary(conn: Connection, season: int | None = None) -> dict[str, Any]:
    return {
        "park_comparison": park_comparison(conn, season),
        "factors": coors_league_index(conn, season),
        "rockies_offense": rockies_offense_splits(conn, season),
        "coors_trend_by_season": seasonal_trend_at_coors(conn),
        "top_hr_stadiums": top_stadiums_by_hr_rate(conn, season),
    }
