# Starts FastAPI server (api.py) from repo root
param(
  [string]$Python="python",
  [int]$Port=5000
)

if (Test-Path .venv\Scripts\Activate.ps1) { . .venv\Scripts\Activate.ps1 }
Write-Host "[start_api] Using Python: $Python"
$env:UVICORN_PORT = $Port
& $Python api.py
