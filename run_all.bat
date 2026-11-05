@echo off
title Restaurant AI - Full Stack Launcher
color 0E
echo =========================================================
echo 🚀 STARTING FULL RESTAURANT AI SYSTEM (Backend + Frontend)
echo =========================================================
echo.

echo 1. Launching Backend on Port 8000...
start "Restaurant AI Backend" cmd /k "%~dp0run_backend.bat"

echo 2. Waiting 3 seconds for Backend to initialize...
timeout /t 3 /nobreak >nul

echo 3. Launching Frontend on Port 3000...
start "Restaurant AI Frontend" cmd /k "%~dp0run_frontend.bat"

echo.
echo ✨ Both Backend & Frontend are running in their respective windows!
echo - Backend API:  http://127.0.0.1:8000
echo - Frontend App: http://localhost:3000
echo.
pause

