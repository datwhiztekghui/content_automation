# Example Windows scheduled task wrapper for headless full runs.
# Adjust paths and create a Task Scheduler job that runs this script.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Error "Create a venv first: python -m venv .venv ; .\.venv\Scripts\pip install -e ."
}

& .\.venv\Scripts\python.exe run.py --mode full --headless --auto-approve --dry-run-media
exit $LASTEXITCODE
