# ETL workflow

## Commands

| Command | Purpose |
|---------|---------|
| `python -m data_pipeline.cli sync-metadata --season 2024` | MLB teams, venues, schedule → PostgreSQL |
| `python -m data_pipeline.cli sync-scores --seasons 2021 2024` | Refresh schedule + final linescores |
| `python -m data_pipeline.cli ingest --season 2024` | Statcast pitch data → `data/cache/statcast/2024/*.parquet` |
| `python -m data_pipeline.cli validate --season 2024` | Quality report JSON (no DB) |
| `python -m data_pipeline.cli load --season 2024` | Cached pitches → `plate_appearances` |
| `python -m data_pipeline.cli run --season 2024` | `ingest` + `load` |

## Plate appearance logic

1. Sort pitches by `game_pk`, `at_bat_number`, `pitch_number`.
2. Take the **terminal pitch** (max `pitch_number`) per at-bat.
3. Map `events` to eight outcome classes (`data_pipeline/transform/outcomes.py`).

## Quality checks

Reports are written to `data/cache/reports/quality-{season}.json` and include duplicate PAs, missing IDs, outcome distribution, and stadium coverage.

## Prerequisites

- PostgreSQL running (`docker compose up postgres -d`)
- `pip install -r data_pipeline/requirements.txt`
- `.env` with `DATABASE_URL`
