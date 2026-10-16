#!/bin/bash
V=/mnt/c/Users/aleja/AppData/Local/hermes/cache/scratch/tsc_venv
B=/mnt/c/Users/aleja/Desktop/github/Transcendence/backend
W=/mnt/c/Users/aleja/AppData/Local/hermes/cache/scratch/poker_audit
cd "$B"
rm -f db.sqlite3
"$V/bin/python" manage.py migrate --noinput >/dev/null 2>&1
export POKER_QUEUE_TIMEOUT=3
export POKER_TURN_TIMEOUT=6
nohup "$V/bin/python" manage.py runserver 127.0.0.1:8011 --noreload >"$W/server_poker.log" 2>&1 &
SRV=$!
for i in $(seq 1 40); do
  if curl -sf http://127.0.0.1:8011/api/health/ >/dev/null 2>&1; then break; fi
  sleep 0.5
done
echo "servidor listo (pid=$SRV)"
"$V/bin/python" "$W/probe_poker_ws2.py"
RC=$?
kill $SRV 2>/dev/null; wait $SRV 2>/dev/null
echo "--- log del servidor (últimas líneas) ---"
tail -12 "$W/server_poker.log"
exit $RC
