Param(
  [string]$Path = "data/config/overrides.render-free.json",
  [string]$ChannelId = "1426571542627614772",
  [int]$Interval = 180
)
if (!(Test-Path $Path)) { Write-Error "[FAIL] $Path not found"; exit 1 }
$raw = Get-Content $Path -Raw -Encoding UTF8
try { $json = $raw | ConvertFrom-Json -ErrorAction Stop } catch { Write-Error "[FAIL] JSON parse: $_"; exit 2 }
if (-not $json.env) { $json | Add-Member -NotePropertyName env -NotePropertyValue (@{}) }
# Normalize accidental quotes
$ChannelId = "$ChannelId".Trim('"').Trim("'")
$json.env.QNA_CHANNEL_ID   = "$ChannelId"
$json.env.QNA_INTERVAL_SEC = "$Interval"
Copy-Item $Path "$Path.bak" -Force
($json | ConvertTo-Json -Depth 50) | Set-Content $Path -Encoding UTF8
Write-Host "[OK] Patched -> QNA_CHANNEL_ID=$ChannelId QNA_INTERVAL_SEC=$Interval"
Write-Host "[OK] Backup -> $Path.bak"
