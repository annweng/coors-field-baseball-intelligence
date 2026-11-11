<#
.SYNOPSIS
  One-shot local dev: Postgres + API + Vite UI (separate terminal windows).
#>
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker is not available. Start Docker Desktop, then run this script again."
}

Write-Host "Starting Postgres..."
docker compose up postgres -d

Write-Host "Waiting for Postgres..."
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    docker compose exec -T postgres pg_isready -U cfbi -d coors_field_bi 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $ready = $true
        break
    }
    Start-Sleep -Seconds 2
}
if (-not $ready) {
    throw "Postgres did not become ready in time. Check: docker compose ps postgres"
}

$portable = Join-Path $root "models\artifacts\xgb-v0.2.2.xgb.json"
if (-not (Test-Path $portable)) {
    Write-Host "Portable forecast model missing; exporting from Docker (one-time)..."
    docker compose --profile train run --rm train python -m models.export_portable xgb-v0.2.2
}

$apiScript = Join-Path $root "scripts\run-api.ps1"
Write-Host "Starting API in a new window..."
Start-Process powershell `
    -WorkingDirectory $root `
    -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $apiScript

Start-Sleep -Seconds 4

Write-Host "Starting frontend in a new window..."
Start-Process powershell `
    -WorkingDirectory (Join-Path $root "frontend") `
    -ArgumentList "-NoExit", "-Command", "npm run dev"

Write-Host ""
Write-Host "Coors Field Baseball Intelligence - dev stack"
Write-Host "  API:      http://localhost:8000/docs"
Write-Host "  UI:       http://localhost:5173"
Write-Host "  Postgres: localhost - see .env DATABASE_URL port, often 5433"
Write-Host ""
Write-Host "Close the API and UI windows to stop those services."
Write-Host 'Stop database: docker compose stop postgres'
