@echo off
setlocal

cd /d "%~dp0\.."
echo Downloading UI assets...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0download_assets.ps1"
if errorlevel 1 (
  echo.
  echo ERROR: Failed to download assets.
  pause
  exit /b 1
)
echo.
echo Done.
pause
