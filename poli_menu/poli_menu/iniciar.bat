@echo off
cd /d "%~dp0"
if not exist .venv ( py -m venv .venv || python -m venv .venv )
call .venv\Scripts\activate.bat
python -m pip install -q -r requirements.txt
python menu.py
pause
