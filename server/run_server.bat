@echo off
title YouTube Downloader API Server
echo ====================================================
echo      Starting YouTube Downloader Backend Server
echo ====================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found in PATH!
    pause
    exit /b 1
)

echo Checking server requirements...
python -c "import flask, flask_cors, yt_dlp" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing requirements...
    python -m pip install -r requirements.txt
)

echo.
echo Server starting at http://localhost:5000 ...
echo (Keep this window open while using the Web App locally)
echo.
python server.py
pause
