@echo off
setlocal

cd /d "%~dp0\.."

if not exist ".venv\Scripts\python.exe" (
  call scripts\setup.bat
  if errorlevel 1 exit /b 1
)

echo.
echo [mylottery] Starting Desktop (Tkinter)...
echo.

".venv\Scripts\python.exe" src\desktop\app.py

