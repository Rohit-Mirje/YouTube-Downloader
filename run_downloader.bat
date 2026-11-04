@echo off
title YouTube Downloader
echo ==============================================
echo       Starting YouTube Media Downloader
echo ==============================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found in your PATH!
    echo Please install Python 3.10+ from python.org and check "Add Python to PATH".
    pause
    exit /b 1
)

echo Checking dependencies...
python -c "import yt_dlp, customtkinter, PIL, requests" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing missing requirements from requirements.txt...
    python -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
)

echo Launching Downloader GUI...
start pythonw youtube_downloader.py
exit
