#!/bin/bash
# Arranca el servidor estático desacoplado de la sesión de wsl.exe.
cd /mnt/c/Users/aleja/AppData/Local/hermes/cache/scratch/poker_audit
pkill -f "ser[v]e.py" 2>/dev/null
sleep 0.5
setsid nohup python3 serve.py > /tmp/serve.log 2>&1 < /dev/null &
disown
sleep 2
echo "log: $(cat /tmp/serve.log)"
echo "procesos: $(pgrep -af 'ser[v]e.py' | tr '\n' ' ')"
