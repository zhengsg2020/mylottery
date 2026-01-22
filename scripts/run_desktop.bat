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
echo [mylottery] 正在启动桌面版(Tkinter)...
echo.

".venv\Scripts\python.exe" "src\desktop\app.py"
