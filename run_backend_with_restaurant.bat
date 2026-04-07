@echo off
REM 启动后端服务（包含美食推荐模块）
echo Starting backend server with restaurant recommendation module...
echo.

cd /d "%~dp0"
python main.py

pause
