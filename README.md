# Coors Field Baseball Intelligence

Independent baseball research and analytics platform focused on Major League Baseball, with emphasis on the Colorado Rockies and park effects at Coors Field.

**Disclaimer:** This is an independent research project. It is not affiliated with the Colorado Rockies, Major League Baseball, or any MLB team.

[![CI](https://github.com/annweng/coors-field-baseball-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/annweng/coors-field-baseball-intelligence/actions/workflows/ci.yml)

## Research objectives

| Product | Description | Status |
|--------|-------------|--------|
| **A — PA forecasting** | Multiclass plate-appearance outcome probabilities (`xgb-v0.2.2`) | Live |
| **B — Coors Field lab** | Park vs league descriptive analytics | Live |
| **C — Team run forecasting** | Expected runs per team (`runs-v0.1.0`, baseline-gated) | Live |

## UI preview

Screenshots are captured locally after running the stack — see [docs/screenshots/README.md](docs/screenshots/README.md) and [docs/runbook.md](docs/runbook.md) §8.

| Area | Route |
|------|--------|
| Overview | `/` |
| Coors Lab | `/coors` |
| Model Lab | `/models` |
| Player Forecasts | `/forecasts` |
| Run Forecasting | `/runs` |

## Technology stack

- **Frontend:** React, TypeScript, Vite, Tailwind CSS, Recharts
- **Backend:** FastAPI, Pydantic, SQLAlchemy
- **Data:** PostgreSQL, Python ETL (`data_pipeline/`)
- **Modeling:** pandas, scikit-learn, XGBoost (Docker train image, Python 3.12)
- **Infrastructure:** Docker Compose, GitHub Actions CI

## Quick start

Full steps: **[docs/runbook.md](docs/runbook.md)**

```powershell
copy .env.example .env
# ... data + models once (see docs/runbook.md) ...
.\scripts\start-dev.ps1
```

Open **http://localhost:5173** · API docs **http://localhost:8000/docs**

## Tests

```powershell
.\scripts\test.ps1
```

CI (`.github/workflows/ci.yml`): Python 3.12 unit + Postgres integration tests, frontend production build.

## Repository layout

```
coors-field-baseball-intelligence/
├── frontend/           # React application
├── backend/            # FastAPI service
├── data_pipeline/      # Statcast ingestion, validation, PA aggregation
├── models/             # Training, evaluation, inference
├── database/           # Schema and migrations
├── tests/              # pytest suite
├── docs/               # Architecture, runbook, dataset notes
├── scripts/            # ingest, train, test helpers
└── docker-compose.yml
```

## Data sources

| Source | Role |
|--------|------|
| [Baseball Savant / Statcast](https://baseballsavant.mlb.com/) | Primary pitch-level data (`pybaseball`) |
| [MLB Stats API](https://statsapi.mlb.com/api/v1/) | Teams, schedule, final scores |
| Local PostgreSQL | Canonical store for PAs, games, evaluations |

Seasons in scope: **2021–2025** (incremental backfill supported).

## Documentation

- [Architecture](docs/architecture.md)
- [Implementation plan](docs/implementation-plan.md)
- [ETL commands](docs/etl.md)
- [ROADMAP](docs/ROADMAP.md)
- [Reproduction runbook](docs/runbook.md)

## Milestone status

| # | Scope | Status |
|---|--------|--------|
| 1 | Scaffold | Done |
| 2 | ETL + PostgreSQL | Done |
| 3 | Dataset validation | Done |
| 4 | Baseline PA model | Done |
| 5–7 | Advanced model, API, UI | Done |
| 8 | Run forecasting | Done (baseline production) |
| 9 | Tests, CI, runbook | Done |

## License

TBD — personal portfolio / research use; respect MLB and third-party data terms.
