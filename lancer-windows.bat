@echo off
cd /d "%~dp0"
echo Preparation d'OSINT-Intel...
python -m pip install --quiet -r requirements.txt
python modules\osint-intel\app.py
pause
