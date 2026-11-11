$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python not found on PATH"
}

pip install -q -r tests\requirements.txt
python -m pytest tests\ -q -m "not integration" @args
if ($env:DATABASE_URL) {
    python -m pytest tests\ -q -m integration @args
} else {
    Write-Host "Skipping integration tests (DATABASE_URL not set)."
}
