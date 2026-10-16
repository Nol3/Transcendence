#!/bin/bash
V=/mnt/c/Users/aleja/AppData/Local/hermes/cache/scratch/tsc_venv
B=/mnt/c/Users/aleja/Desktop/github/Transcendence/backend
W=/mnt/c/Users/aleja/AppData/Local/hermes/cache/scratch/poker_audit
cd "$B"
rm -f db.sqlite3
"$V/bin/python" manage.py migrate --noinput >/dev/null 2>&1
nohup "$V/bin/python" manage.py runserver 127.0.0.1:8011 --noreload >"$W/server.log" 2>&1 &
SRV=$!
for i in $(seq 1 40); do
  if curl -sf http://127.0.0.1:8011/api/health/ >/dev/null 2>&1; then break; fi
  sleep 0.5
done
echo "servidor pid=$SRV listo tras ${i} intentos"
"$V/bin/python" "$W/probe.py"
RC=$?
kill $SRV 2>/dev/null
wait $SRV 2>/dev/null
echo "--- ultimas lineas del log del servidor ---"
tail -6 "$W/server.log"
exit $RC
