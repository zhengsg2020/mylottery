@echo off
setlocal

cd /d "%~dp0\.."

echo.
echo [mylottery] Setup (Windows)
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo ERROR: 未找到 python。请先安装 Python 3 并勾选 "Add Python to PATH"。
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/2] 创建虚拟环境 .venv ...
  python -m venv .venv
  if errorlevel 1 (
    echo ERROR: 创建虚拟环境失败。
    pause
    exit /b 1
  )
)

echo [2/2] 安装依赖 requirements.txt ...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo ERROR: 安装依赖失败。
  pause
  exit /b 1
)

echo.
echo OK: 环境已就绪。
pause
exit /b 0

