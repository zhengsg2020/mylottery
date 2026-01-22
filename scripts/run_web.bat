@echo off
chcp 65001 >nul
setlocal
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
cd /d "%~dp0\.."

if not exist ".venv\Scripts\python.exe" (
  call scripts\setup.bat
  if errorlevel 1 exit /b 1
)

echo.
echo [mylottery] 正在启动 Web(Flask)...
echo URL: http://127.0.0.1:5000
echo 按 Ctrl+C 停止。
echo.

start "" "http://127.0.0.1:5000"
".venv\Scripts\python.exe" "src\web\app.py"
