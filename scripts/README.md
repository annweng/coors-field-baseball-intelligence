# Scripts

| Script | Purpose |
|--------|---------|
| **`start-dev.ps1`** | **One command:** Postgres + API window + UI window |
| `stop-dev.ps1` | Stop Postgres (close API/UI windows yourself) |
| `run-api.ps1` | FastAPI on port 8000 with repo `.env` |
| `ingest_season.ps1` | Statcast ingest + load for one season |
| `backfill_seasons.ps1` | Multi-season PA backfill |
| `sync-scores.ps1` | Migration 002 + MLB linescores |
| `train_xgb.ps1` | Docker XGB PA training |
| `train_runs.ps1` | Docker team-runs training |
| `test.ps1` | Local pytest (unit; integration if `DATABASE_URL` set) |
