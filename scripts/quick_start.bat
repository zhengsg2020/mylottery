@echo off
setlocal

rem Fix garbled Chinese on some Windows consoles by switching to UTF-8
for /f "tokens=2 delims=: " %%a in ('chcp') do set "_OLD_CP=%%a"
chcp 65001 >nul

cd /d "%~dp0\.."

echo ========================================
echo   至尊彩票大师 - 快速启动
echo ========================================
echo.
echo 请选择运行模式：
echo.
echo [1] 桌面版 (Tkinter GUI)
echo [2] 网页版 (Flask Web)
echo [3] 安装/更新依赖
echo [4] 下载UI资源
echo [5] 退出
echo.
set /p choice="请输入选项 (1-5): "

if "%choice%"=="1" (
  call "%~dp0run_desktop.bat"
) else if "%choice%"=="2" (
  call "%~dp0run_web.bat"
) else if "%choice%"=="3" (
  call "%~dp0setup.bat"
) else if "%choice%"=="4" (
  call "%~dp0download_assets.bat"
) else if "%choice%"=="5" (
  exit /b 0
) else (
  echo 无效选项！
  pause
)

if defined _OLD_CP chcp %_OLD_CP% >nul
endlocal

