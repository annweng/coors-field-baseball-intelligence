"""ORM models matching database/init/001_schema.sql."""

import enum
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Double,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PaOutcome(str, enum.Enum):
    strikeout = "strikeout"
    walk = "walk"
    hit_by_pitch = "hit_by_pitch"
    single = "single"
    double = "double"
    triple = "triple"
    home_run = "home_run"
    other_out = "other_out"
    unknown = "unknown"


class Team(Base):
    __tablename__ = "teams"

    mlb_team_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    abbreviation: Mapped[str | None] = mapped_column(String(10))
    league: Mapped[str | None] = mapped_column(String(50))
    division: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Stadium(Base):
    __tablename__ = "stadiums"

    stadium_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    primary_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.mlb_team_id"))
    city: Mapped[str | None] = mapped_column(String(80))
    capacity: Mapped[int | None] = mapped_column(Integer)
    altitude_ft: Mapped[int | None] = mapped_column(Integer)
    is_coors_field: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Player(Base):
    __tablename__ = "players"

    mlb_player_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    bats: Mapped[str | None] = mapped_column(String(1))
    throws: Mapped[str | None] = mapped_column(String(1))
    primary_position: Mapped[str | None] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Game(Base):
    __tablename__ = "games"

    game_pk: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    game_date: Mapped[date] = mapped_column(Date, nullable=False)
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.mlb_team_id"), nullable=False)
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.mlb_team_id"), nullable=False)
    stadium_id: Mapped[int | None] = mapped_column(ForeignKey("stadiums.stadium_id"))
    game_type: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str | None] = mapped_column(String(40))
    home_score: Mapped[int | None] = mapped_column(Integer)
    away_score: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PlateAppearance(Base):
    __tablename__ = "plate_appearances"
    __table_args__ = (
        UniqueConstraint("game_pk", "at_bat_number", name="uq_plate_appearance"),
        Index("idx_pa_batter_date", "batter_id", "game_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    game_pk: Mapped[int] = mapped_column(BigInteger, ForeignKey("games.game_pk"), nullable=False)
    at_bat_number: Mapped[int] = mapped_column(Integer, nullable=False)
    batter_id: Mapped[int] = mapped_column(ForeignKey("players.mlb_player_id"), nullable=False)
    pitcher_id: Mapped[int] = mapped_column(ForeignKey("players.mlb_player_id"), nullable=False)
    game_date: Mapped[date] = mapped_column(Date, nullable=False)
    inning: Mapped[int | None] = mapped_column(Integer)
    inning_topbot: Mapped[str | None] = mapped_column(String(3))
    outs_when_up: Mapped[int | None] = mapped_column(Integer)
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.mlb_team_id"), nullable=False)
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.mlb_team_id"), nullable=False)
    stadium_id: Mapped[int | None] = mapped_column(ForeignKey("stadiums.stadium_id"))
    batter_stands: Mapped[str | None] = mapped_column(String(1))
    pitcher_throws: Mapped[str | None] = mapped_column(String(1))
    outcome: Mapped[PaOutcome] = mapped_column(
        Enum(PaOutcome, name="pa_outcome", create_constraint=False, native_enum=True),
        default=PaOutcome.unknown,
        nullable=False,
    )
    events_raw: Mapped[str | None] = mapped_column(String(80))
    description_raw: Mapped[str | None] = mapped_column(String(120))
    pitches_in_pa: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    source_retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EtlRun(Base):
    __tablename__ = "etl_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    pipeline: Mapped[str] = mapped_column(String(64), nullable=False)
    season: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="running", nullable=False)
    rows_affected: Mapped[int | None] = mapped_column(Integer)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class ModelEvaluation(Base):
    __tablename__ = "model_evaluations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    evaluation_type: Mapped[str] = mapped_column(String(40), nullable=False)
    train_start: Mapped[date | None] = mapped_column(Date)
    train_end: Mapped[date | None] = mapped_column(Date)
    test_start: Mapped[date | None] = mapped_column(Date)
    test_end: Mapped[date | None] = mapped_column(Date)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
