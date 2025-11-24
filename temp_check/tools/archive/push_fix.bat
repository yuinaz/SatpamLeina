@echo off
setlocal enabledelayedexpansion
REM === push_fix.bat ===
REM Usage: push_fix.bat "your commit message"

REM Ganti ke folder repo kamu
cd /d G:\DiscordBot\SatpamBot

REM Quick sanity check
if not exist .git (
  echo [ERROR] This folder is not a Git repository. Open the repo folder and try again.
  pause
  exit /b 1
)

REM Commit message
set MSG=%*
if "%MSG%"=="" (
  for /f "tokens=1-2 delims= " %%a in ('date /t') do set TODAY=%%a %%b
  for /f "tokens=1 delims=." %%t in ("%time%") do set NOW=%%t
  set MSG=Quick push: !TODAY! !NOW!
)

echo.
echo [1/3] Staging changes under 'modules'...
git add modules

echo [2/3] Committing...
git commit -m "%MSG%" 2>nul
if errorlevel 1 (
  echo (Nothing to commit or commit failed — continuing to push anyway.)
)

echo [3/3] Pushing to origin...
for /f "delims=" %%b in ('git rev-parse --abbrev-ref HEAD') do set BRANCH=%%b
if "%BRANCH%"=="" set BRANCH=main
git push origin %BRANCH%

echo.
echo Done. Current branch: %BRANCH%
pause
