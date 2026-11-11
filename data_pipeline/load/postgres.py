"""Load transformed data into PostgreSQL."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import EtlRun, Game, PaOutcome, Player, PlateAppearance, Stadium, Team
from data_pipeline.ingest.mlb_api import fetch_games_for_season, fetch_teams, fetch_venues

logger = logging.getLogger(__name__)

CHUNK_SIZE = 2000


def _upsert_teams(session: Session, teams: list[dict[str, Any]]) -> None:
    for row in teams:
        stmt = insert(Team).values(**row)
        stmt = stmt.on_conflict_do_update(
            index_elements=[Team.mlb_team_id],
            set_={
                "name": stmt.excluded.name,
                "abbreviation": stmt.excluded.abbreviation,
                "league": stmt.excluded.league,
                "division": stmt.excluded.division,
            },
        )
        session.execute(stmt)


def _upsert_stadiums(session: Session, venues: list[dict[str, Any]]) -> None:
    for row in venues:
        stmt = insert(Stadium).values(
            stadium_id=row["stadium_id"],
            name=row["name"],
            city=row.get("city"),
            capacity=row.get("capacity"),
            is_coors_field=row.get("is_coors_field", False),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[Stadium.stadium_id],
            set_={
                "name": stmt.excluded.name,
                "city": stmt.excluded.city,
                "capacity": stmt.excluded.capacity,
                "is_coors_field": stmt.excluded.is_coors_field,
            },
        )
        session.execute(stmt)


def sync_mlb_metadata(session: Session, season: int) -> dict[str, int]:
    teams = fetch_teams()
    venues = fetch_venues()
    games = fetch_games_for_season(season)

    _upsert_teams(session, teams)
    _upsert_stadiums(session, venues)

    game_rows: list[dict[str, Any]] = []
    for g in games:
        if not g.get("home_team_id") or not g.get("away_team_id"):
            continue
        game_rows.append(
            {
                "game_pk": g["game_pk"],
                "game_date": date.fromisoformat(g["game_date"]),
                "season": g["season"],
                "home_team_id": g["home_team_id"],
                "away_team_id": g["away_team_id"],
                "stadium_id": g.get("stadium_id"),
                "game_type": g.get("game_type"),
                "status": g.get("status"),
                "home_score": g.get("home_score"),
                "away_score": g.get("away_score"),
            }
        )

    # Schedule hydrate can return duplicate game_pk rows in one response.
    deduped: dict[int, dict[str, Any]] = {}
    for row in game_rows:
        deduped[int(row["game_pk"])] = row
    game_rows = list(deduped.values())

    for i in range(0, len(game_rows), CHUNK_SIZE):
        chunk = game_rows[i : i + CHUNK_SIZE]
        stmt = insert(Game).values(chunk)
        stmt = stmt.on_conflict_do_update(
            index_elements=[Game.game_pk],
            set_={
                "status": stmt.excluded.status,
                "stadium_id": stmt.excluded.stadium_id,
                "home_score": stmt.excluded.home_score,
                "away_score": stmt.excluded.away_score,
            },
        )
        session.execute(stmt)

    session.commit()
    return {"teams": len(teams), "stadiums": len(venues), "games": len(game_rows)}


def ensure_teams(session: Session) -> dict[str, int]:
    count = session.scalar(select(func.count()).select_from(Team)) or 0
    if count == 0:
        _upsert_teams(session, fetch_teams())
        session.commit()
    return team_abbrev_map_from_db(session)


def team_abbrev_map_from_db(session: Session) -> dict[str, int]:
    teams = session.execute(select(Team)).scalars().all()
    return {str(t.abbreviation).upper(): t.mlb_team_id for t in teams if t.abbreviation}


def _bulk_upsert_players(session: Session, pa_df: pd.DataFrame) -> None:
    players: dict[int, dict[str, Any]] = {}

    for _, row in pa_df.iterrows():
        bid = int(row["batter"])
        pid = int(row["pitcher"])
        if bid not in players:
            players[bid] = {
                "mlb_player_id": bid,
                "full_name": row["batter_name"]
                if pd.notna(row.get("batter_name"))
                else f"MLB Player {bid}",
                "bats": str(row["stand"]) if pd.notna(row.get("stand")) else None,
                "throws": None,
            }
        elif pd.notna(row.get("batter_name")):
            players[bid]["full_name"] = row["batter_name"]
            if pd.notna(row.get("stand")):
                players[bid]["bats"] = str(row["stand"])

        if pid not in players:
            players[pid] = {
                "mlb_player_id": pid,
                "full_name": row["pitcher_name_col"]
                if pd.notna(row.get("pitcher_name_col"))
                else f"MLB Player {pid}",
                "bats": None,
                "throws": str(row["p_throws"]) if pd.notna(row.get("p_throws")) else None,
            }
        else:
            if pd.notna(row.get("pitcher_name_col")):
                players[pid]["full_name"] = row["pitcher_name_col"]
            if pd.notna(row.get("p_throws")):
                players[pid]["throws"] = str(row["p_throws"])

    rows = list(players.values())

    for i in range(0, len(rows), CHUNK_SIZE):
        chunk = rows[i : i + CHUNK_SIZE]
        stmt = insert(Player).values(chunk)
        stmt = stmt.on_conflict_do_update(
            index_elements=[Player.mlb_player_id],
            set_={"full_name": stmt.excluded.full_name, "bats": stmt.excluded.bats, "throws": stmt.excluded.throws},
        )
        session.execute(stmt)


def _bulk_upsert_games(session: Session, pa_df: pd.DataFrame, team_map: dict[str, int]) -> None:
    games = pa_df.drop_duplicates(subset=["game_pk"])
    rows: list[dict[str, Any]] = []
    for _, row in games.iterrows():
        home_id = team_map.get(str(row["home_team"]).upper())
        away_id = team_map.get(str(row["away_team"]).upper())
        if home_id is None or away_id is None:
            continue
        game_date = row["game_date"]
        if isinstance(game_date, str):
            game_date = date.fromisoformat(game_date)
        season = game_date.year if game_date.month >= 3 else game_date.year - 1
        stadium_id = int(row["venue_id"]) if pd.notna(row.get("venue_id")) else None
        rows.append(
            {
                "game_pk": int(row["game_pk"]),
                "game_date": game_date,
                "season": season,
                "home_team_id": home_id,
                "away_team_id": away_id,
                "stadium_id": stadium_id,
                "game_type": "R",
            }
        )

    for i in range(0, len(rows), CHUNK_SIZE):
        chunk = rows[i : i + CHUNK_SIZE]
        stmt = insert(Game).values(chunk)
        stmt = stmt.on_conflict_do_nothing(index_elements=[Game.game_pk])
        session.execute(stmt)


def _bulk_upsert_stadiums_from_pa(session: Session, pa_df: pd.DataFrame) -> None:
    if "venue_id" not in pa_df.columns:
        return
    venues = pa_df.dropna(subset=["venue_id"]).drop_duplicates(subset=["venue_id"])
    rows: list[dict[str, Any]] = []
    for _, row in venues.iterrows():
        name = str(row.get("venue_name") or f"Venue {int(row['venue_id'])}")
        rows.append(
            {
                "stadium_id": int(row["venue_id"]),
                "name": name,
                "is_coors_field": "coors" in name.lower(),
            }
        )
    for i in range(0, len(rows), CHUNK_SIZE):
        chunk = rows[i : i + CHUNK_SIZE]
        stmt = insert(Stadium).values(chunk)
        stmt = stmt.on_conflict_do_nothing(index_elements=[Stadium.stadium_id])
        session.execute(stmt)


def load_plate_appearances(
    session: Session,
    pa_df: pd.DataFrame,
    *,
    team_abbrev_map: dict[str, int],
) -> int:
    if pa_df.empty:
        return 0

    _bulk_upsert_players(session, pa_df)
    _bulk_upsert_stadiums_from_pa(session, pa_df)
    _bulk_upsert_games(session, pa_df, team_abbrev_map)
    session.commit()

    pa_rows: list[dict[str, Any]] = []
    for _, row in pa_df.iterrows():
        home_id = team_abbrev_map.get(str(row["home_team"]).upper())
        away_id = team_abbrev_map.get(str(row["away_team"]).upper())
        if home_id is None or away_id is None:
            continue
        game_date = row["game_date"]
        if isinstance(game_date, str):
            game_date = date.fromisoformat(game_date)
        stadium_id = int(row["venue_id"]) if pd.notna(row.get("venue_id")) else None
        events_raw = row.get("events")
        desc = row.get("description")
        retrieved_at = row.get("source_retrieved_at")

        pa_rows.append(
            {
                "game_pk": int(row["game_pk"]),
                "at_bat_number": int(row["at_bat_number"]),
                "batter_id": int(row["batter"]),
                "pitcher_id": int(row["pitcher"]),
                "game_date": game_date,
                "inning": int(row["inning"]) if pd.notna(row.get("inning")) else None,
                "inning_topbot": str(row["inning_topbot"]) if pd.notna(row.get("inning_topbot")) else None,
                "outs_when_up": int(row["outs_when_up"]) if pd.notna(row.get("outs_when_up")) else None,
                "home_team_id": home_id,
                "away_team_id": away_id,
                "stadium_id": stadium_id,
                "batter_stands": str(row["stand"]) if pd.notna(row.get("stand")) else None,
                "pitcher_throws": str(row["p_throws"]) if pd.notna(row.get("p_throws")) else None,
                "outcome": PaOutcome(str(row["outcome"])),
                "events_raw": str(events_raw) if pd.notna(events_raw) else None,
                "description_raw": str(desc) if pd.notna(desc) else None,
                "pitches_in_pa": int(row["pitches_in_pa"]),
                "source_retrieved_at": retrieved_at,
            }
        )

    inserted = 0
    for i in range(0, len(pa_rows), CHUNK_SIZE):
        chunk = pa_rows[i : i + CHUNK_SIZE]
        stmt = insert(PlateAppearance).values(chunk)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_plate_appearance",
            set_={
                "outcome": stmt.excluded.outcome,
                "events_raw": stmt.excluded.events_raw,
                "pitches_in_pa": stmt.excluded.pitches_in_pa,
            },
        )
        session.execute(stmt)
        inserted += len(chunk)
    session.commit()
    return inserted


def record_etl_run(
    session: Session,
    pipeline: str,
    season: int | None,
    status: str,
    rows: int | None,
    details: dict[str, Any] | None,
) -> None:
    run = EtlRun(
        pipeline=pipeline,
        season=season,
        finished_at=datetime.now(timezone.utc),
        status=status,
        rows_affected=rows,
        details=details,
    )
    session.add(run)
    session.commit()


def create_session(database_url: str) -> Session:
    engine = create_engine(database_url, pool_pre_ping=True)
    return sessionmaker(bind=engine)()
