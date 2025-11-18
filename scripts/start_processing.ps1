# Starts processing (main.py) from repo root
param(
  [string]$Python="python",
  [string]$Config="config.json"
)

if (Test-Path .venv\Scripts\Activate.ps1) { . .venv\Scripts\Activate.ps1 }
Write-Host "[start_processing] Using Python: $Python"
if (-Not (Test-Path $Config)) { Write-Warning "Config file '$Config' not found." }
& $Python main.py
