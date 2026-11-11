"""Coors Field research API (descriptive statistics)."""

from fastapi import APIRouter, HTTPException, Query

from app.db.session import engine
from app.services.coors import (
    park_comparison,
    rockies_offense_splits,
    seasonal_trend_at_coors,
    summary,
    top_stadiums_by_hr_rate,
)

router = APIRouter(prefix="/coors", tags=["coors"])


@router.get("/summary")
def coors_summary(season: int | None = Query(None, ge=2021, le=2025)) -> dict:
    try:
        with engine.connect() as conn:
            return summary(conn, season)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/park-comparison")
def coors_park_comparison(season: int | None = Query(None, ge=2021, le=2025)) -> dict:
    with engine.connect() as conn:
        return park_comparison(conn, season)


@router.get("/rockies-splits")
def coors_rockies_splits(season: int | None = Query(None, ge=2021, le=2025)) -> dict:
    with engine.connect() as conn:
        return rockies_offense_splits(conn, season)


@router.get("/trends")
def coors_trends() -> dict:
    with engine.connect() as conn:
        return {"seasons": seasonal_trend_at_coors(conn)}


@router.get("/stadiums/hr-rates")
def stadium_hr_rates(season: int | None = Query(None, ge=2021, le=2025), limit: int = 12) -> dict:
    with engine.connect() as conn:
        return {"season": season, "stadiums": top_stadiums_by_hr_rate(conn, season, limit)}
