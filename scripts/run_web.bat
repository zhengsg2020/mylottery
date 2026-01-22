@echo off
setlocal

cd /d "%~dp0\.."

if not exist ".venv\Scripts\python.exe" (
  call scripts\setup.bat
  if errorlevel 1 exit /b 1
)

echo.
echo [mylottery] Starting Web (Flask)...
echo.
echo 默认地址: http://127.0.0.1:5000
echo 关闭请按 Ctrl+C
echo.

start "" "http://127.0.0.1:5000"
".venv\Scripts\python.exe" src\web\app.py

