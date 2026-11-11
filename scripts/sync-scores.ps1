$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

Get-Content "database\migrations\002_game_scores.sql" | docker compose exec -T postgres psql -U cfbi -d coors_field_bi

python -m data_pipeline.cli sync-scores --seasons 2021 2022 2023 2024 2025
