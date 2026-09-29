$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Venv = Join-Path $Root ".venv"
if (-not (Test-Path $Venv)) {
    py -3.11 -m venv $Venv
}
& (Join-Path $Venv "Scripts\python.exe") -m pip install --upgrade pip
& (Join-Path $Venv "Scripts\python.exe") -m pip install -e "$Root[dev]"
Write-Host "Setup complete. Run scripts\run.ps1"

