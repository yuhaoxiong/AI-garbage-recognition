@echo off
REM 废弃物AI识别指导投放系统 - 启动脚本
REM 自动使用venv虚拟环境运行

echo ========================================
echo 废弃物AI识别指导投放系统
echo ========================================
echo.
echo 正在使用虚拟环境启动...
echo.

REM 使用venv中的Python运行程序
.\.venv\Scripts\python.exe .\main.py

echo.
echo 程序已退出
pause
