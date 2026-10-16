#!/bin/bash
set -e
V=/mnt/c/Users/aleja/AppData/Local/hermes/cache/scratch/tsc_venv
B=/mnt/c/Users/aleja/Desktop/github/Transcendence/backend
export PATH="$HOME/.local/bin:$PATH"
if [ ! -d "$V" ]; then
  uv venv --python 3.11 "$V"
fi
uv pip install --python "$V/bin/python" -q -r "$B/requirements.txt"
uv pip install --python "$V/bin/python" -q websockets
"$V/bin/python" -V
cd "$B"
echo "=== manage.py check ==="
"$V/bin/python" manage.py check 2>&1 | tail -20
echo "=== migrate ==="
"$V/bin/python" manage.py migrate --noinput 2>&1 | tail -8
echo "=== tests torneo ==="
"$V/bin/python" manage.py test apps.tournament.tests -v 1 2>&1 | tail -15
echo "=== apps instaladas / URL map relevante ==="
"$V/bin/python" - <<'PY'
import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE","config.settings")
django.setup()
from django.urls import get_resolver
def walk(res, prefix=""):
    for p in res.url_patterns:
        if hasattr(p,'url_patterns'):
            walk(p, prefix+str(p.pattern))
        else:
            yield prefix+str(p.pattern)
urls = sorted(set(walk(get_resolver())))
for u in urls:
    if any(k in u for k in ('rooms','matchmaking','games','tournament','game-embed','users','leaderboard','public')):
        print("  ", u)
print("TOTAL rutas:", len(urls))
PY
