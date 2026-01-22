@echo off
setlocal
cd /d "%~dp0\.."

:menu
cls
echo ================================
echo   mylottery - Quick Start
echo ================================
echo 1. 安装/更新依赖 (setup)
echo 2. 启动网页版 (Flask)
echo 3. 启动桌面版 (Tkinter)
echo 4. 退出
echo.

set /p choice=请选择 [1-4] :
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

