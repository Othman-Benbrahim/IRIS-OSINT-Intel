#!/bin/bash
cd "$(dirname "$0")"
echo "Préparation d'OSINT-Intel…"
python3 -m pip install --quiet --user -r requirements.txt 2>/dev/null
python3 modules/osint-intel/app.py
