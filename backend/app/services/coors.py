"""Coors Field and park-effect analytics (descriptive)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

ROCKIES_TEAM_ID = 115
# Statcast venue ids for Coors + Rockies home games when PA.stadium_id is null
COORS_VENUE_IDS = (19, 3312)

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


def _coors_pa_sql() -> str:
    """Plate appearances treated as at Coors Field (handles missing pa.stadium_id)."""
    return """
        (
            pa.stadium_id = ANY(:coors_ids)
            OR g.stadium_id = ANY(:coors_ids)
            OR g.home_team_id = :rockies_id
        )
    """


def _coors_params(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    base = {"coors_ids": list(COORS_VENUE_IDS), "rockies_id": ROCKIES_TEAM_ID}
    if extra:
        base.update(extra)
    return base


def park_comparison(conn: Connection, season: int | None = None) -> dict[str, Any]:
    where, params = _season_filter(season)
    coors = conn.execute(
        text(
            f"""
            SELECT 'coors' AS site, {OUTCOME_RATE_SQL}
            FROM plate_appearances pa
            JOIN games g ON g.game_pk = pa.game_pk
            WHERE pa.outcome::text != 'unknown'
              AND {_coors_pa_sql()} {where}
            """
        ),
        _coors_params(params),
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
    def _idx(num: float | None, den: float | None) -> float | None:
        if num is None or den is None or den == 0:
            return None
        return float(num) / float(den)

    return {
        "hr_index": _idx(c.get("hr_rate"), L.get("hr_rate")),
        "hit_index": _idx(c.get("hit_rate"), L.get("hit_rate")),
        "k_index": _idx(c.get("k_rate"), L.get("k_rate")),
        "bb_index": _idx(c.get("bb_rate"), L.get("bb_rate")),
        "double_index": _idx(c.get("double_rate"), L.get("double_rate")),
        "sample_pa_coors": int(c.get("pa") or 0),
        "sample_pa_league": int(L.get("pa") or 0),
    }


def rockies_offense_splits(conn: Connection, season: int | None = None) -> dict[str, Any]:
    """Rockies batting PAs: at Coors vs all other venues."""
    where, params = _season_filter(season)
    rows = conn.execute(
        text(
            f"""
            SELECT
              CASE
                WHEN g.home_team_id = :team_id AND UPPER(pa.inning_topbot) = 'BOT' THEN 'at_coors'
                ELSE 'away_from_coors'
              END AS split,
              {OUTCOME_RATE_SQL}
            FROM plate_appearances pa
            JOIN games g ON g.game_pk = pa.game_pk
            WHERE pa.outcome::text != 'unknown'
              AND (
                (g.home_team_id = :team_id AND UPPER(pa.inning_topbot) = 'BOT')
                OR (g.away_team_id = :team_id AND UPPER(pa.inning_topbot) = 'TOP')
              )
              {where}
            GROUP BY 1
            """
        ),
        {**_coors_params(params), "team_id": ROCKIES_TEAM_ID},
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
            WHERE pa.outcome::text != 'unknown'
              AND {_coors_pa_sql()}
            GROUP BY g.season
            ORDER BY g.season
            """
        ),
        _coors_params(),
    ).mappings().all()
    return [dict(r) for r in rows]


def top_stadiums_by_hr_rate(conn: Connection, season: int | None = None, limit: int = 10) -> list[dict[str, Any]]:
    where, params = _season_filter(season)
    rows = conn.execute(
        text(
            f"""
            SELECT
              COALESCE(s.name, 'Venue ' || resolved_venue::text) AS name,
              resolved_venue AS stadium_id,
              (resolved_venue = ANY(:coors_ids)) AS is_coors_field,
              {OUTCOME_RATE_SQL}
            FROM plate_appearances pa
            JOIN games g ON g.game_pk = pa.game_pk
            LEFT JOIN stadiums s ON s.stadium_id = COALESCE(
                pa.stadium_id,
                g.stadium_id,
                CASE WHEN g.home_team_id = :rockies_id THEN 19 END
            )
            CROSS JOIN LATERAL (
              SELECT COALESCE(
                pa.stadium_id,
                g.stadium_id,
                CASE WHEN g.home_team_id = :rockies_id THEN 19 END
              ) AS resolved_venue
            ) v
            WHERE pa.outcome::text != 'unknown' {where}
            GROUP BY resolved_venue, s.name
            HAVING COUNT(*) >= 500
            ORDER BY hr_rate DESC
            LIMIT :lim
            """
        ),
        {**_coors_params({**params, "lim": limit})},
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
