# Ingest + load a Statcast season (requires PostgreSQL; start with: docker compose up postgres -d)
param(
    [int]$Season = 2024,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if ($Force) {
    python -m data_pipeline.cli run --season $Season --force
} else {
    python -m data_pipeline.cli run --season $Season
}
