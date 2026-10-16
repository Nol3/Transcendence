#!/bin/bash
V=/mnt/c/Users/aleja/AppData/Local/hermes/cache/scratch/tsc_venv
B=/mnt/c/Users/aleja/Desktop/github/Transcendence/backend
cd "$B"
echo "=== check ==="
"$V/bin/python" manage.py check 2>&1 | tail -5
echo "=== tests del motor de poker ==="
"$V/bin/python" manage.py test apps.poker -v 2 2>&1 | tail -60
