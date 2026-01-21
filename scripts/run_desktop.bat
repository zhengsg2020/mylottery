@echo off
setlocal

cd /d "%~dp0\.."

if not exist ".venv\Scripts\python.exe" (
  echo ERROR: .venv not found. Please run scripts\setup.bat first.
  echo.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" src\desktop\app.py

pause
