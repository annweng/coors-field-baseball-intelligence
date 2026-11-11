"""Teams, players, stadiums lookup."""

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from app.db.session import engine

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
    return {"players": [dict(r) for r in rows]}


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
