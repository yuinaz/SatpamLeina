@echo off
REM build_minipc_exe.bat — INTERACTIVE + COGS FIX (basis kamu, 1 file)
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
title Build EXE — SatpamLeina (interactive)

set "LOG=%~dp0build_exe.log"
echo # Build started > "%LOG%"

echo [1/6] Deteksi Python dari "py -0p"...
set "PYEXE="
for %%V in (3.11 3.10 3.12 3.9) do (
  for /f "delims=" %%P in ('py -0p 2^>NUL ^| findstr /r "\-%%V\-"') do (
    set "PYEXE=py -%%V"
    goto :py_ok
  )
)
where python >NUL 2>&1 && set "PYEXE=python"
:py_ok
if not defined PYEXE (
  echo [ERROR] Python 3.11/3.10/3.12/3.9 tidak ditemukan. >> "%LOG%"
  echo [ERROR] Python tidak ditemukan. Pastikan Python terpasang.
  goto :fail
)
echo   -> Memakai: %PYEXE%
echo [INFO] PYEXE=%PYEXE% >> "%LOG%"

REM ===== path repo =====
set "REPO=%~1"
if "%REPO%"=="" set /p REPO=Masukkan path repo (folder yang ADA main.py): 
if not exist "%REPO%\main.py" (
  echo [ERROR] main.py tidak ditemukan di "%REPO%". >> "%LOG%"
  echo [ERROR] main.py tidak ditemukan di path tsb.
  goto :fail
)

REM ===== entry (basis kamu) =====
set "ENTRY=%~dp0minipc_app.py"
if not exist "%ENTRY%" (
  echo [ERROR] minipc_app.py tidak ada di folder ini. >> "%LOG%"
  echo [ERROR] minipc_app.py tidak ada di folder ini.
  goto :fail
)

echo [2/6] Upgrade pip/wheel (progress di log)...
%PYEXE% -m pip install --upgrade pip wheel  >> "%LOG%" 2>&1
powershell -NoLogo -NoProfile -Command "Get-Content -Path '%LOG%' -Tail 10"
if errorlevel 1 goto :fail

echo [3/6] Pastikan PyInstaller terpasang...
%PYEXE% -m pip show pyinstaller >NUL 2>&1 || %PYEXE% -m pip install "pyinstaller>=6.0"  >> "%LOG%" 2>&1
powershell -NoLogo -NoProfile -Command "Get-Content -Path '%LOG%' -Tail 10"
if errorlevel 1 goto :fail

echo [4/6] Smoke import (cek import main & satpambot)...
set "TMP=%TEMP%\smoke_minipc_%RANDOM%.py"
>  "%TMP%" echo import sys
>> "%TMP%" echo sys.path.insert(0, r"%REPO%")
>> "%TMP%" echo print("[TEST] sys.path[0] =", sys.path[0])
>> "%TMP%" echo try:
>> "%TMP%" echo     import main as _entry; print("[TEST] import main: OK")
>> "%TMP%" echo except Exception as e:
>> "%TMP%" echo     print("[TEST] import main: FAIL ->", e)
>> "%TMP%" echo try:
>> "%TMP%" echo     import satpambot as _sp; print("[TEST] import satpambot: OK", getattr(_sp,"__file__","?"))
>> "%TMP%" echo except Exception as e:
>> "%TMP%" echo     print("[TEST] import satpambot: FAIL ->", e)
%PYEXE% -X utf8 "%TMP%" >> "%LOG%" 2>&1
del "%TMP%" >nul 2>&1
powershell -NoLogo -NoProfile -Command "Get-Content -Path '%LOG%' -Tail 10"

echo [5/6] Build EXE (ini agak lama, lihat tail log di bawah)...
%PYEXE% -m PyInstaller --name "SatpamLeinaLocal" --onefile --clean --noconfirm --console ^
  --paths "%REPO%" ^
  --collect-all satpambot ^
  --collect-all satpambot.bot ^
  --collect-all satpambot.bot.modules ^
  --collect-all satpambot.bot.modules.discord_bot ^
  --collect-all satpambot.bot.modules.discord_bot.cogs ^
  --collect-submodules satpambot.bot.modules.discord_bot.cogs ^
  --hidden-import=satpambot.bot.modules.discord_bot.shim_runner ^
  "%ENTRY%"  >> "%LOG%" 2>&1

powershell -NoLogo -NoProfile -Command "Get-Content -Path '%LOG%' -Tail 25"
if errorlevel 1 (
  echo [ERROR] Build gagal. Lihat %LOG%.
  goto :fail
)

echo [6/6] Selesai.
echo [OK] EXE: dist\SatpamLeinaLocal.exe
echo.
pause
exit /b 0

:fail
echo.
echo ====== TAIL build_exe.log ======
powershell -NoLogo -NoProfile -Command "Get-Content -Path '%LOG%' -Tail 80" 2>nul
echo =================================
echo Lihat log lengkap: %LOG%
echo.
pause
exit /b 1