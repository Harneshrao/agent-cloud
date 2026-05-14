@echo off
cd /d "%~dp0"
echo Starting Agent Cloud API at http://localhost:8000 ...
echo.
py -3.11 run_backend.py
pause
