@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
cd /d "%~dp0\.."

echo.
echo [mylottery] 初始化环境(Windows)
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo 错误：未找到 python。请安装 Python 3，并勾选"Add Python to PATH"。
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/2] 正在创建虚拟环境：.venv ...
  python -m venv .venv
  if errorlevel 1 (
    echo 错误：创建虚拟环境失败。
    pause
    exit /b 1
  )
)

rem 从 pip 配置/环境变量读取 index-url；若是 http 镜像则自动添加 trusted-host
set "INDEX_URL="
for /f "usebackq delims=" %%i in (`".venv\Scripts\python.exe" -m pip config get global.index-url 2^>nul`) do set "INDEX_URL=%%i"
if not defined INDEX_URL if defined PIP_INDEX_URL set "INDEX_URL=%PIP_INDEX_URL%"
if not defined INDEX_URL set "INDEX_URL=https://pypi.org/simple"

set "TRUSTED_HOST="
if /i "!INDEX_URL:~0,7!"=="http://" (
  set "URL_NO_PROTO=!INDEX_URL:~7!"
  for /f "tokens=1 delims=/" %%h in ("!URL_NO_PROTO!") do set "HOST_PORT=%%h"
  for /f "tokens=1 delims=:" %%h in ("!HOST_PORT!") do set "TRUSTED_HOST=%%h"
)

set "PIP_ARGS=--index-url !INDEX_URL!"
if defined TRUSTED_HOST set "PIP_ARGS=!PIP_ARGS! --trusted-host !TRUSTED_HOST!"

echo [2/2] 正在安装依赖...
echo - index-url: !INDEX_URL!
if defined TRUSTED_HOST echo - trusted-host: !TRUSTED_HOST!

".venv\Scripts\python.exe" -m pip install --upgrade pip %PIP_ARGS%
".venv\Scripts\python.exe" -m pip install -r requirements.txt %PIP_ARGS%
if errorlevel 1 (
  echo.
  echo 错误：依赖安装失败。
  echo 如果你使用的是内网 HTTP 镜像，请确认它允许并已信任。
  echo 当前参数：%PIP_ARGS%
  echo.
  pause
  exit /b 1
)

echo.
echo 完成：环境已初始化。
pause
exit /b 0
