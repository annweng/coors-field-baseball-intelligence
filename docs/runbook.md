# Reproduction runbook

End-to-end steps to run **Coors Field Baseball Intelligence** on a clean machine (Windows-focused; Linux/macOS analogous).

## Prerequisites

| Tool | Version |
|------|---------|
| Docker Desktop | running |
| Python | 3.12+ recommended (3.14 OK for pipeline/API; use Docker for XGBoost training) |
| Node.js | 20+ |
| Git | any recent |

## 1. Clone and configure

```powershell
git clone <your-remote> coors-field-baseball-intelligence
cd coors-field-baseball-intelligence
copy .env.example .env
```

If port **5432** is taken locally, set `POSTGRES_PORT=5433` in `.env` and:

```env
DATABASE_URL=postgresql+psycopg://cfbi:cfbi_dev_password@localhost:5433/coors_field_bi
```

## 2. Database

```powershell
docker compose up postgres -d
```

Existing DB created before Milestone 8:

```powershell
Get-Content database\migrations\002_game_scores.sql | docker compose exec -T postgres psql -U cfbi -d coors_field_bi
```

## 3. Python dependencies

```powershell
pip install -r tests\requirements.txt
```

## 4. Data (minimum demo)

**Quick (2024 only):**

```powershell
python -m data_pipeline.cli sync-metadata --season 2024
python -m data_pipeline.cli run --season 2024
```

**Full backfill (2021–2025):**

```powershell
.\scripts\backfill_seasons.ps1
.\scripts\sync-scores.ps1
```

Validate:

```powershell
python -m data_pipeline.cli profile-dataset --seasons 2024
```

## 5. Models

| Model | Command |
|-------|---------|
| Baseline PA | `python -m models.train_baseline --seasons 2024` |
| Production PA (XGB) | `.\scripts\train_xgb.ps1` |
| Team runs | `.\scripts\train_runs.ps1` (after `sync-scores`) |

Artifacts land in `models/artifacts/` (gitignored). Gates:

- `active_model.json` → `beats_baseline` for XGB forecasts
- `active_runs_model.json` → Ridge vs runs baseline MAE

## 6. API and UI

```powershell
.\scripts\run-api.ps1
```

Separate terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**

| Page | Depends on |
|------|------------|
| Overview / Coors Lab | Postgres + PAs |
| Model Lab | Eval JSON under `data/cache/reports/` + DB optional |
| Player Forecasts | Postgres + `xgb-v0.2.2` artifact |
| Run Forecasting | Postgres scores + `runs-v0.1.0` artifact |

## 7. Tests and CI

Local:

```powershell
.\scripts\test.ps1
```

With integration (Postgres up, `DATABASE_URL` in `.env`):

```powershell
$env:DATABASE_URL = "postgresql+psycopg://cfbi:cfbi_dev_password@localhost:5433/coors_field_bi"
pytest tests/ -q
```

GitHub Actions runs unit + integration tests and `npm run build` on push/PR (see `.github/workflows/ci.yml`).

## 8. Screenshots (README)

Capture after UI is running:

1. **Overview** — stat cards populated
2. **Coors Lab** — HR rate chart
3. **Model Lab** — calibration charts + eval table
4. **Player Forecasts** — matchup probabilities
5. **Run Forecasting** — team run lines

Save as `docs/screenshots/overview.png`, etc., and reference in README.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| API ECONNREFUSED on 8000 | `.\scripts\run-api.ps1`; check `.env` DATABASE_URL port |
| Empty Coors/Forecasts | Finish ETL load; confirm `docker compose ps` healthy |
| Forecasts 503 | Train XGB in Docker; confirm `active_model.json` |
| Runs 503 | `sync-scores` + `train_runs` |
| pybaseball errors | `pybaseball.cache.enable()`; check network |
