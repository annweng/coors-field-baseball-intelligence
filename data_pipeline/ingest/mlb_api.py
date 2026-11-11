"""Sync teams, venues, and schedule metadata from MLB Stats API."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

import httpx

MLB_API = "https://statsapi.mlb.com/api/v1"
COORS_VENUE_NAMES = {"coors field"}

logger = logging.getLogger(__name__)


def _get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"{MLB_API}{path}"
    with httpx.Client(timeout=60.0) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()


def fetch_teams() -> list[dict[str, Any]]:
    data = _get("/teams", {"sportId": 1, "season": date.today().year})
    teams: list[dict[str, Any]] = []
    for entry in data.get("teams", []):
        league = entry.get("league", {}) or {}
        division = entry.get("division", {}) or {}
        teams.append(
            {
                "mlb_team_id": entry["id"],
                "name": entry.get("name", ""),
                "abbreviation": entry.get("abbreviation"),
                "league": league.get("name"),
                "division": division.get("name"),
            }
        )
    return teams


def fetch_venues() -> list[dict[str, Any]]:
    data = _get("/venues")
    venues: list[dict[str, Any]] = []
    for entry in data.get("venues", []):
        location = entry.get("location", {}) or {}
        name = entry.get("name", "")
        venues.append(
            {
                "stadium_id": entry["id"],
                "name": name,
                "city": location.get("city"),
                "capacity": entry.get("capacity"),
                "is_coors_field": name.lower() in COORS_VENUE_NAMES,
            }
        )
    return venues


def fetch_games_for_season(season: int) -> list[dict[str, Any]]:
    """Regular season game list via sport schedule endpoint."""
    data = _get(
        "/schedule",
        {
            "sportId": 1,
            "season": season,
            "gameType": "R",
            "hydrate": "team,venue,linescore",
        },
    )
    games: list[dict[str, Any]] = []
    for day in data.get("dates", []):
        game_date = day.get("date")
        for g in day.get("games", []):
            teams = g.get("teams", {})
            home = teams.get("home", {}).get("team", {})
            away = teams.get("away", {}).get("team", {})
            venue = g.get("venue", {}) or {}
            abstract = (g.get("status") or {}).get("abstractGameState")
            home_score = None
            away_score = None
            if abstract == "Final":
                ls_teams = (g.get("linescore") or {}).get("teams") or {}
                if "home" in ls_teams and "away" in ls_teams:
                    home_score = ls_teams["home"].get("runs")
                    away_score = ls_teams["away"].get("runs")
            games.append(
                {
                    "game_pk": g["gamePk"],
                    "game_date": game_date,
                    "season": season,
                    "home_team_id": home.get("id"),
                    "away_team_id": away.get("id"),
                    "stadium_id": venue.get("id"),
                    "game_type": g.get("gameType"),
                    "status": (g.get("status") or {}).get("detailedState"),
                    "home_score": home_score,
                    "away_score": away_score,
                }
            )
    return games


def abbreviation_to_team_id(teams: list[dict[str, Any]]) -> dict[str, int]:
    return {
        str(t["abbreviation"]).upper(): int(t["mlb_team_id"])
        for t in teams
        if t.get("abbreviation")
    }
