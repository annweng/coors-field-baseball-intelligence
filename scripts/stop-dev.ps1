$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
Write-Host "Stopping Postgres container..."
docker compose stop postgres
Write-Host "Close any open 'run-api' and 'npm run dev' PowerShell windows manually."
