@echo off
setlocal

cd /d "%~dp0\.."

if not exist ".venv\Scripts\python.exe" (
  echo ERROR: .venv not found. Please run scripts\setup.bat first.
  echo.
  pause
  exit /b 1
)

echo Starting web server on http://127.0.0.1:5000 ...
".venv\Scripts\python.exe" src\web\app.py

pause
