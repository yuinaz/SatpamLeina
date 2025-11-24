@echo off
REM Wrapper to run the smoke script with a persistent window. No Python required.
REM If you prefer, set the env here (uncomment next 2 lines):
REM set "UPSTASH_REDIS_REST_URL=https://xxxxx.upstash.io"
REM set "UPSTASH_REDIS_REST_TOKEN=AYJhbGciOiJIUzI1NiIsInR5cCI…"
"C:\Program Files\Git\bin\bash.exe" -lc "bash './scripts/smoke_xp_consistency.sh'"
echo.
pause
