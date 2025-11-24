
@echo off
setlocal enabledelayedexpansion
if "%BASE%"=="" (
  echo [!] Set BASE first, e.g.:
  echo     set BASE=https://satpambot-31l5.onrender.com
  goto :eof
)
echo BASE=%BASE%
if "%AUTH%"=="" (
  echo AUTH not set (will call without Authorization header)
) else (
  echo AUTH=%AUTH%
)

set paths=healthz get/learning:status get/learning:status_json api/get/learning:status api/get/learning:status_json learning/status learning:status

echo ----
for %%p in (%paths%) do (
  set url=%BASE%/%%p
  if "%AUTH%"=="" (
    curl -s -o nul -w "%%{http_code}  !url!\n" "!url!"
  ) else (
    curl -s -o nul -w "%%{http_code}  !url!\n" -H "%AUTH%" "!url!"
  )
)
