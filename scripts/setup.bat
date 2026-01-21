@echo off
setlocal enabledelayedexpansion

REM One-click setup (venv + deps) and run for Windows
REM Requires: Python 3.x in PATH

cd /d "%~dp0\.."

echo [1/3] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
  echo.
  echo ERROR: Python not found in PATH.
  echo Please install Python 3 and check "Add python.exe to PATH".
  echo.
  pause
  exit /b 1
)

echo [2/3] Creating/using virtual environment...
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
  if errorlevel 1 (
    echo.
    echo ERROR: Failed to create venv.
    pause
    exit /b 1
  )
)

echo [3/3] Installing dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo ERROR: pip install failed.
  pause
  exit /b 1
)

echo.
echo Setup completed successfully!
echo.
echo To run desktop app: scripts\run_desktop.bat
echo To run web app: scripts\run_web.bat
echo.
pause
