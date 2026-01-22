@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
cd /d "%~dp0\.."

:menu
cls
echo ==================================
echo   mylottery - 快速启动
echo ==================================
echo 1. 初始化环境(创建 venv + 安装依赖)
echo 2. 运行 Web(Flask)
echo 3. 运行桌面版(Tkinter)
echo 4. 退出
echo.

set "choice="
set /p choice=请选择 [1-4]:
if "%choice%"=="1" goto setup
if "%choice%"=="2" goto web
if "%choice%"=="3" goto desktop
if "%choice%"=="4" goto end

echo 输入无效，请重试...
timeout /t 1 >nul
goto menu

:setup
call scripts\setup.bat
goto menu

:web
call scripts\run_web.bat
goto menu

:desktop
call scripts\run_desktop.bat
goto menu

:end
exit /b 0
