@echo off
cd /d "%~dp0"
echo Setting up Python 3.11 environment...

py -3.11 -m venv .venv

call .venv\Scripts\activate

pip install --upgrade pip

pip install pip-tools

pip install -r requirements.txt

echo.
echo Environment ready.
echo Activate with:
echo .venv\Scripts\activate
pause
