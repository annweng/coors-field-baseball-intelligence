-- Add final scores to games (Milestone 8 run forecasting)

ALTER TABLE games
    ADD COLUMN IF NOT EXISTS home_score INTEGER,
    ADD COLUMN IF NOT EXISTS away_score INTEGER;

CREATE INDEX IF NOT EXISTS idx_games_scores ON games (season)
    WHERE home_score IS NOT NULL AND away_score IS NOT NULL;
