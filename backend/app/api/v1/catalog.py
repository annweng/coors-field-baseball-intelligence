"""Teams, players, stadiums lookup."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import engine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["catalog"])


@router.get("/teams")
def list_teams() -> dict:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT mlb_team_id, name, abbreviation, league, division FROM teams ORDER BY name"
            )
        ).mappings().all()
    return {"teams": [dict(r) for r in rows]}


@router.get("/stadiums")
def list_stadiums() -> dict:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT stadium_id, name, city, is_coors_field
                FROM stadiums
                WHERE stadium_id IN (
                    SELECT DISTINCT stadium_id FROM plate_appearances WHERE stadium_id IS NOT NULL
                )
                ORDER BY name
                LIMIT 200
                """
            )
        ).mappings().all()
    return {"stadiums": [dict(r) for r in rows]}


@router.get("/players/search")
def search_players(q: str = Query(..., min_length=2), limit: int = Query(25, le=50)) -> dict:
    """Name search via MLB Stats API (canonical names), with DB fallback."""
    merged: dict[int, dict] = {}

    try:
        from data_pipeline.ingest.mlb_api import search_people

        for row in search_people(q, limit=limit):
            merged[int(row["mlb_player_id"])] = row
    except Exception as exc:  # noqa: BLE001
        logger.warning("MLB people search failed: %s", exc)

    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT mlb_player_id, full_name, bats, throws, primary_position
                    FROM players
                    WHERE full_name ILIKE :pattern
                    ORDER BY full_name
                    LIMIT :lim
                    """
                ),
                {"pattern": f"%{q}%", "lim": limit},
            ).mappings().all()
        for r in rows:
            pid = int(r["mlb_player_id"])
            if pid not in merged:
                merged[pid] = dict(r)
    except SQLAlchemyError as exc:
        if not merged:
            raise HTTPException(status_code=503, detail=f"database_unavailable: {exc}") from exc

    players = sorted(merged.values(), key=lambda p: str(p.get("full_name", "")))[:limit]
    return {"players": players}


@router.get("/players/{player_id}/availability")
def player_availability(player_id: int, season: int = Query(2024, ge=2021, le=2025)) -> dict:
    """PA counts in DB by role — use before running forecasts."""
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT
                  SUM(CASE WHEN pa.batter_id = :pid THEN 1 ELSE 0 END) AS pa_as_batter,
                  SUM(CASE WHEN pa.pitcher_id = :pid THEN 1 ELSE 0 END) AS pa_as_pitcher
                FROM plate_appearances pa
                JOIN games g ON g.game_pk = pa.game_pk
                WHERE g.season = :season
                  AND pa.outcome::text != 'unknown'
                  AND (pa.batter_id = :pid OR pa.pitcher_id = :pid)
                """
            ),
            {"pid": player_id, "season": season},
        ).mappings().first()
    batt = int(row["pa_as_batter"] or 0) if row else 0
    pitch = int(row["pa_as_pitcher"] or 0) if row else 0
    return {
        "mlb_player_id": player_id,
        "season": season,
        "pa_as_batter": batt,
        "pa_as_pitcher": pitch,
        "forecast_ok_batter": batt > 0,
        "forecast_ok_pitcher": pitch > 0,
    }


@router.get("/players/{player_id}/summary")
def player_summary(player_id: int, season: int | None = None) -> dict:
    season_sql = "AND g.season = :season" if season else ""
    params: dict = {"pid": player_id}
    if season:
        params["season"] = season
    with engine.connect() as conn:
        row = conn.execute(
            text(
                f"""
                SELECT p.full_name,
                  COUNT(*) AS pa,
                  AVG(CASE WHEN pa.outcome::text = 'home_run' THEN 1.0 ELSE 0.0 END) AS hr_rate,
                  AVG(CASE WHEN pa.outcome::text = 'strikeout' THEN 1.0 ELSE 0.0 END) AS k_rate,
                  AVG(CASE WHEN pa.outcome::text = 'walk' THEN 1.0 ELSE 0.0 END) AS bb_rate,
                  AVG(CASE WHEN pa.outcome::text IN ('single','double','triple','home_run') THEN 1.0 ELSE 0.0 END) AS hit_rate
                FROM plate_appearances pa
                JOIN players p ON p.mlb_player_id = pa.batter_id
                JOIN games g ON g.game_pk = pa.game_pk
                WHERE pa.batter_id = :pid AND pa.outcome::text != 'unknown' {season_sql}
                GROUP BY p.full_name
                """
            ),
            params,
        ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="player_not_found")
    return dict(row)
