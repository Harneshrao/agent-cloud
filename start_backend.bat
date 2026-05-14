@echo off
cd /d "%~dp0"

call .venv\Scripts\activate

echo Starting Agent Cloud backend...

python run_backend.py
pause
