#!/bin/bash
V=/mnt/c/Users/aleja/AppData/Local/hermes/cache/scratch/tsc_venv
B=/mnt/c/Users/aleja/Desktop/github/Transcendence/backend
W=/mnt/c/Users/aleja/AppData/Local/hermes/cache/scratch/poker_audit
cd "$B"
rm -f db.sqlite3
"$V/bin/python" manage.py migrate --noinput >/dev/null 2>&1
export POKER_QUEUE_TIMEOUT=3
export POKER_TURN_TIMEOUT=12
nohup setsid "$V/bin/python" manage.py runserver 127.0.0.1:8000 --noreload >"$W/server_ui.log" 2>&1 < /dev/null &
for i in $(seq 1 40); do
  curl -sf http://127.0.0.1:8000/api/health/ >/dev/null 2>&1 && break
  sleep 0.5
done
echo "backend listo en :8000"
