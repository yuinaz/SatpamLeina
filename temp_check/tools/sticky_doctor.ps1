param([switch]$Fix = $false, [switch]$Hard = $false)
$Root     = (Resolve-Path "$PSScriptRoot\..").Path
$CogsDir  = Join-Path $Root 'satpambot/bot/modules/discord_bot/cogs'
$Loader   = Join-Path $Root 'satpambot/bot/modules/discord_bot/cogs_loader.py'
$AppDash  = Join-Path $Root 'satpambot/dashboard/app_dashboard.py'
$AppFall  = Join-Path $Root 'satpambot/dashboard/app_fallback.py'
$EnvLocal = Join-Path $Root '.env.local'
$PatchPy  = Join-Path $Root 'scripts/patch_healthz.py'

Write-Host "== Sticky Doctor v3 (PowerShell) =="
Write-Host "ROOT=$Root"

if ($Fix) {
  if (Test-Path $Loader) {
    $txt = Get-Content $Loader -Raw
    $new = [regex]::Replace($txt,'DISABLED_COGS\s*=\s*set\(\(os\.getenv\("DISABLED_COGS"\)\s*or\s*".*?"\)\.split\(",\"\)\)\)','DISABLED_COGS = set((os.getenv("DISABLED_COGS") or "image_poster,sticky_guard,status_sticky_patched").split(","))',1)
    if ($new -ne $txt) { Copy-Item $Loader "$Loader.bak" -Force; Set-Content $Loader $new -Encoding UTF8; Write-Host "  -> Patched loader default" }
  }
  $line = 'DISABLED_COGS=image_poster,sticky_guard,status_sticky_patched'
  if (Test-Path $EnvLocal) {
    $txt = Get-Content $EnvLocal -Raw
    if ($txt -match '^DISABLED_COGS=') {
      $new = [regex]::Replace($txt,'^DISABLED_COGS=.*','DISABLED_COGS=image_poster,sticky_guard,status_sticky_patched',[System.Text.RegularExpressions.RegexOptions]::Multiline)
      Set-Content $EnvLocal $new -Encoding UTF8
    } else {
      Add-Content $EnvLocal $line
    }
  } else { Set-Content $EnvLocal $line -Encoding UTF8 }
  Write-Host "  -> Wrote $EnvLocal"
  if (Test-Path $AppDash) { python $PatchPy $AppDash }
  if (Test-Path $AppFall) { python $PatchPy $AppFall }
  if ($Hard) {
    Get-ChildItem $CogsDir -Filter status_sticky_patched.py -ErrorAction SilentlyContinue | ForEach-Object { Rename-Item $_.FullName ($_.FullName + ".disabled") -Force }
    Get-ChildItem $CogsDir -Filter sticky_guard.py -ErrorAction SilentlyContinue | ForEach-Object { Rename-Item $_.FullName ($_.FullName + ".disabled") -Force }
  }
}
Write-Host "Done. Restart services."
