<#
Run local setup for SatpamLeina (PowerShell)

What this does:
- Creates a virtualenv at .venv (if missing)
- Installs pinned dependencies from requirements.txt
- Runs quick predeploy and smoke checks
- Optionally starts the bot (requires secrets in env or .env)

Usage:
  pwsh -ExecutionPolicy Bypass -File .\scripts\run_local.ps1 -InstallDeps -Smoke -StartBot

Parameters:
  -InstallDeps   : create venv and install requirements.txt
  -Smoke         : run predeploy_check.py and scripts/smoke_all.py
  -StartBot      : run main.py (requires DISCORD_TOKEN and other env vars)
#>

param(
    [switch]$InstallDeps,
    [switch]$Smoke,
    [switch]$StartBot
)

Set-StrictMode -Version Latest
Push-Location $PSScriptRoot\.. | Out-Null

$venvPath = Join-Path $PWD '.venv'
$python = Join-Path $venvPath 'Scripts\python.exe'

function Ensure-Venv {
    if (-not (Test-Path $venvPath)) {
        Write-Host "Creating virtualenv at $venvPath..."
        py -3 -m venv $venvPath
    } else {
        Write-Host "Using existing virtualenv at $venvPath"
    }
}

function Install-Requirements {
    Ensure-Venv
    Write-Host "Installing requirements (this may take a while)..."
    & $python -m pip install --upgrade pip setuptools wheel
    & $python -m pip install -r requirements.txt
}

function Run-Smoke {
    Ensure-Venv
    Write-Host "Running predeploy_render_free_check.py..."
    & $python predeploy_render_free_check.py
    Write-Host "Running smoke_all.py..."
    & $python scripts/smoke_all.py
}

function Start-Bot {
    Ensure-Venv
    if (-not $env:DISCORD_TOKEN) {
        Write-Warning "DISCORD_TOKEN not set in environment; bot will not start. Set env var or use a .env loader."
        return
    }
    Write-Host "Starting bot (main.py) — attach logs to console..."
    & $python main.py
}

if ($InstallDeps) { Install-Requirements }
if ($Smoke) { Run-Smoke }
if ($StartBot) { Start-Bot }

Pop-Location | Out-Null
