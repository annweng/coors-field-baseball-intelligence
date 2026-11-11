$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

docker compose --profile train build train
docker compose --profile train run --rm train `
  python -m models.train_advanced `
  --seasons 2021 2022 2023 2024 `
  --train-end 2024-07-31 `
  --val-end 2024-08-31 `
  --test-end 2024-10-31 `
  --calibration none
