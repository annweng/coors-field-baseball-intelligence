$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$env:PYTHONPATH = "$root;$root\backend"
Set-Location "$root\backend"

# Load repo-root .env into process environment for uvicorn
$envFile = Join-Path $root ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            Set-Item -Path "env:$name" -Value $value
        }
    }
}

python -c "import xgboost" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing forecast dependencies (xgboost, sklearn, joblib)..."
    python -m pip install -q scikit-learn joblib xgboost
}

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
