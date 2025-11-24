# scripts/xp_fix_senior_total.ps1
param()

if (-not $env:UPSTASH_REDIS_REST_URL -or -not $env:UPSTASH_REDIS_REST_TOKEN) {
  Write-Error "Please set UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN"
  exit 1
}

$Key = "xp:bot:senior_total"
$Headers = @{ Authorization = "Bearer $env:UPSTASH_REDIS_REST_TOKEN" }

Write-Host "[check] GET $Key"
$res = Invoke-RestMethod -Uri "$($env:UPSTASH_REDIS_REST_URL)/get/$Key" -Headers $Headers -Method Get
$raw = $res.result

function Is-Integer([string]$s) { return $s -match '^-?\d+$' }

if (Is-Integer $raw) {
  Write-Host "[ok] Already integer: $raw"
  exit 0
}

try {
  $obj = $raw | ConvertFrom-Json -ErrorAction Stop
  if ($obj.PSObject.Properties.Name -contains "senior_total_xp") {
    $val = [int]$obj.senior_total_xp
    Write-Host "[fix] SET $Key -> $val"
    $set = Invoke-RestMethod -Uri "$($env:UPSTASH_REDIS_REST_URL)/set/$Key/$val" -Headers $Headers -Method Post
    $set | ConvertTo-Json -Depth 3
  } else {
    Write-Warning "Cannot coerce value: $raw"
    exit 2
  }
} catch {
  Write-Warning "Cannot parse: $raw"
  exit 2
}
