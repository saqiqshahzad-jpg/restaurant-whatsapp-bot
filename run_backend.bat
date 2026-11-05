@echo off
title Restaurant AI Backend (Port 8000)
color 0A
echo =========================================================
echo 🍔 RESTAURANT AI BOT - FASTAPI BACKEND SERVER 🍔
echo =========================================================
echo Starting on http://127.0.0.1:8000 ...
echo.

cd /d "%~dp0backend"
python main.py

if errorlevel 1 (
    echo.
    echo [ERROR] Backend band ho gaya. Neeche error check karein:
    pause
)

