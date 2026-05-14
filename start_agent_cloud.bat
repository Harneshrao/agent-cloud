@echo off
cd /d "%~dp0"

call .venv\Scripts\activate

echo Starting Agent Cloud Platform...

python run_all.py

pause
