-- Coors Field Baseball Intelligence — initial schema (Milestone 2)

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE teams (
    mlb_team_id     INTEGER PRIMARY KEY,
    name            VARCHAR(120) NOT NULL,
    abbreviation    VARCHAR(10),
    league          VARCHAR(50),
    division        VARCHAR(50),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE stadiums (
    stadium_id      INTEGER PRIMARY KEY,
    name            VARCHAR(120) NOT NULL,
    primary_team_id INTEGER REFERENCES teams(mlb_team_id),
    city            VARCHAR(80),
    capacity        INTEGER,
    altitude_ft     INTEGER,
    is_coors_field  BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE players (
    mlb_player_id   INTEGER PRIMARY KEY,
    full_name       VARCHAR(120) NOT NULL,
    bats            CHAR(1),
    throws          CHAR(1),
    primary_position VARCHAR(10),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE games (
    game_pk         BIGINT PRIMARY KEY,
    game_date       DATE NOT NULL,
    season          INTEGER NOT NULL,
    home_team_id    INTEGER NOT NULL REFERENCES teams(mlb_team_id),
    away_team_id    INTEGER NOT NULL REFERENCES teams(mlb_team_id),
    stadium_id      INTEGER REFERENCES stadiums(stadium_id),
    game_type       VARCHAR(20),
    status          VARCHAR(40),
    home_score      INTEGER,
    away_score      INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT games_season_date_chk CHECK (season >= 1900 AND season <= 2100)
);

CREATE INDEX idx_games_date ON games (game_date);
CREATE INDEX idx_games_season ON games (season);
CREATE INDEX idx_games_home_team ON games (home_team_id);

CREATE TYPE pa_outcome AS ENUM (
    'strikeout',
    'walk',
    'hit_by_pitch',
    'single',
    'double',
    'triple',
    'home_run',
    'other_out',
    'unknown'
);

CREATE TABLE plate_appearances (
    id              BIGSERIAL PRIMARY KEY,
    game_pk         BIGINT NOT NULL REFERENCES games(game_pk),
    at_bat_number   INTEGER NOT NULL,
    batter_id       INTEGER NOT NULL REFERENCES players(mlb_player_id),
    pitcher_id      INTEGER NOT NULL REFERENCES players(mlb_player_id),
    game_date       DATE NOT NULL,
    inning          INTEGER,
    inning_topbot   VARCHAR(3),
    outs_when_up    INTEGER,
    home_team_id    INTEGER NOT NULL REFERENCES teams(mlb_team_id),
    away_team_id    INTEGER NOT NULL REFERENCES teams(mlb_team_id),
    stadium_id      INTEGER REFERENCES stadiums(stadium_id),
    batter_stands   CHAR(1),
    pitcher_throws  CHAR(1),
    outcome         pa_outcome NOT NULL DEFAULT 'unknown',
    events_raw      VARCHAR(80),
    description_raw VARCHAR(120),
    pitches_in_pa   INTEGER NOT NULL DEFAULT 1,
    source_retrieved_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_plate_appearance UNIQUE (game_pk, at_bat_number),
    CONSTRAINT outs_when_up_chk CHECK (outs_when_up IS NULL OR outs_when_up BETWEEN 0 AND 2)
);

CREATE INDEX idx_pa_game ON plate_appearances (game_pk);
CREATE INDEX idx_pa_batter_date ON plate_appearances (batter_id, game_date);
CREATE INDEX idx_pa_pitcher_date ON plate_appearances (pitcher_id, game_date);
CREATE INDEX idx_pa_stadium ON plate_appearances (stadium_id);
CREATE INDEX idx_pa_outcome ON plate_appearances (outcome);

CREATE TABLE player_game_stats (
    id              BIGSERIAL PRIMARY KEY,
    game_pk         BIGINT NOT NULL REFERENCES games(game_pk),
    mlb_player_id   INTEGER NOT NULL REFERENCES players(mlb_player_id),
    role            VARCHAR(20) NOT NULL,
    plate_appearances INTEGER NOT NULL DEFAULT 0,
    hits            INTEGER NOT NULL DEFAULT 0,
    home_runs       INTEGER NOT NULL DEFAULT 0,
    walks           INTEGER NOT NULL DEFAULT 0,
    strikeouts      INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_player_game UNIQUE (game_pk, mlb_player_id, role)
);

CREATE TABLE player_rolling_stats (
    id              BIGSERIAL PRIMARY KEY,
    mlb_player_id   INTEGER NOT NULL REFERENCES players(mlb_player_id),
    as_of_date      DATE NOT NULL,
    window_days     INTEGER NOT NULL,
    pa              INTEGER NOT NULL DEFAULT 0,
    k_rate          DOUBLE PRECISION,
    bb_rate         DOUBLE PRECISION,
    hr_rate         DOUBLE PRECISION,
    woba            DOUBLE PRECISION,
    xwoba           DOUBLE PRECISION,
    avg_exit_velo   DOUBLE PRECISION,
    hard_hit_pct    DOUBLE PRECISION,
    barrel_rate     DOUBLE PRECISION,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_player_rolling UNIQUE (mlb_player_id, as_of_date, window_days)
);

CREATE TABLE pitcher_rolling_stats (
    id              BIGSERIAL PRIMARY KEY,
    mlb_player_id   INTEGER NOT NULL REFERENCES players(mlb_player_id),
    as_of_date      DATE NOT NULL,
    window_days     INTEGER NOT NULL,
    batters_faced   INTEGER NOT NULL DEFAULT 0,
    k_rate          DOUBLE PRECISION,
    bb_rate         DOUBLE PRECISION,
    whiff_rate      DOUBLE PRECISION,
    avg_velocity    DOUBLE PRECISION,
    era             DOUBLE PRECISION,
    fip             DOUBLE PRECISION,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_pitcher_rolling UNIQUE (mlb_player_id, as_of_date, window_days)
);

CREATE TABLE model_predictions (
    id              BIGSERIAL PRIMARY KEY,
    model_version   VARCHAR(64) NOT NULL,
    prediction_type VARCHAR(40) NOT NULL,
    game_pk         BIGINT,
    mlb_player_id   INTEGER REFERENCES players(mlb_player_id),
    as_of_date      DATE NOT NULL,
    payload         JSONB NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE model_evaluations (
    id              BIGSERIAL PRIMARY KEY,
    model_version   VARCHAR(64) NOT NULL,
    evaluation_type VARCHAR(40) NOT NULL,
    train_start     DATE,
    train_end       DATE,
    test_start      DATE,
    test_end        DATE,
    metrics         JSONB NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE etl_runs (
    id              BIGSERIAL PRIMARY KEY,
    pipeline        VARCHAR(64) NOT NULL,
    season          INTEGER,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    status          VARCHAR(20) NOT NULL DEFAULT 'running',
    rows_affected   INTEGER,
    details         JSONB
);
