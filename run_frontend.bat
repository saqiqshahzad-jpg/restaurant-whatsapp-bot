@echo off
title Restaurant AI Frontend (Port 3000)
color 0B
echo =========================================================
echo 🌐 RESTAURANT AI BOT - REACT FRONTEND (UI) 🌐
echo =========================================================
echo Starting on http://localhost:3000 ...
echo.

cd /d "%~dp0frontend"
npm start

if errorlevel 1 (
    echo.
    echo [ERROR] Frontend start hone mein masla aaya:
    pause
)

