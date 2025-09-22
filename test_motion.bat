@echo off
echo 启动运动检测测试界面...
echo.

REM 检查Python环境
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 错误：未找到Python环境
    echo 请确保已安装Python并添加到环境变量
    pause
    exit /b 1
)

REM 启动测试界面
python test_motion_detection.py

REM 如果程序异常退出，暂停显示错误信息
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo 程序异常退出，错误代码: %ERRORLEVEL%
    pause
) 