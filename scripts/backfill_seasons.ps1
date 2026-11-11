# Ingest + load Statcast seasons into PostgreSQL (skip if already cached/loaded).
param(
    [int[]]$Seasons = @(2021, 2022, 2023, 2024, 2025)
)

$ErrorActionPreference = "Continue"
Set-Location (Split-Path $PSScriptRoot -Parent)

foreach ($season in $Seasons) {
    Write-Host "==== Season $season ===="
    python -m data_pipeline.cli ingest --season $season
    if ($LASTEXITCODE -ne 0) { Write-Warning "Ingest failed for $season" }
    python -m data_pipeline.cli sync-metadata --season $season
    python -m data_pipeline.cli load --season $season
    if ($LASTEXITCODE -ne 0) { Write-Warning "Load failed for $season" }
}

python -m data_pipeline.cli profile-dataset --seasons 2021 2022 2023 2024 2025
Write-Host "Backfill complete."
