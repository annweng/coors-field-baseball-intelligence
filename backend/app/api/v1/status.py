"""Operational status including database connectivity."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.db.session import engine

router = APIRouter()


@router.get("/status")
def service_status() -> dict:
    try:
        with engine.connect() as conn:
            pa_count = conn.execute(text("SELECT COUNT(*) FROM plate_appearances")).scalar_one()
            team_count = conn.execute(text("SELECT COUNT(*) FROM teams")).scalar_one()
    except Exception as exc:  # noqa: BLE001 — surface DB errors to operators
        raise HTTPException(status_code=503, detail=f"database_unavailable: {exc}") from exc

    return {
        "database": "ok",
        "teams": int(team_count),
        "plate_appearances": int(pa_count),
    }
