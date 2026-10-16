#!/bin/bash
# Auditoría de integridad y privacidad contra un stack en marcha.
#
#   bash scripts/audit/audit_integrity.sh [https://localhost:8443]
#
# Comprueba, con peticiones reales, los tres hallazgos P0 de docs/AUDITORIA_PROYECTO.md:
#   A1  ¿se puede fabricar una victoria y subir ELO desde el cliente?
#   C1  ¿el listado de usuarios expone emails?
#   B1  ¿la app de chat devuelve 500?
set -u
BASE="${1:-https://localhost:8443}"
U="audit$RANDOM$RANDOM"

reg=$(curl -sk -X POST "$BASE/api/auth/register/" -H "Content-Type: application/json" \
      -d "{\"username\":\"$U\",\"email\":\"$U@example.com\",\"password\":\"Zx9!pqLmn42\"}")
TOK=$(echo "$reg" | python -c "import sys,json;print(json.load(sys.stdin)['data']['tokens']['accessToken'])" 2>/dev/null)
if [ -z "${TOK:-}" ]; then echo "No se pudo registrar el usuario de prueba: $reg"; exit 1; fi
echo "usuario de prueba: $U"
AUTH=(-H "Authorization: Bearer $TOK")

echo
echo "== A1) ¿Se puede autootorgar una victoria y subir ELO? =="
antes=$(curl -sk "${AUTH[@]}" "$BASE/api/users/me/stats/" | python -c "import sys,json;print(json.load(sys.stdin)['data'])")
echo "  stats antes:  $antes"
GID=$(curl -sk -X POST "${AUTH[@]}" -H "Content-Type: application/json" -d '{}' \
      "$BASE/api/games/create_game/" | python -c "import sys,json;print(json.load(sys.stdin)['id'])" 2>/dev/null)
code=$(curl -sk -o /dev/null -w "%{http_code}" -X POST "${AUTH[@]}" -H "Content-Type: application/json" \
      -d "{\"winner\":\"$U\",\"player1_score\":9999,\"player2_score\":0}" "$BASE/api/games/$GID/finish/")
echo "  finish() -> HTTP $code"
despues=$(curl -sk "${AUTH[@]}" "$BASE/api/users/me/stats/" | python -c "import sys,json;print(json.load(sys.stdin)['data'])")
echo "  stats después: $despues"
elo=$(curl -sk "$BASE/api/leaderboard/" | python -c "
import sys,json
d=json.load(sys.stdin)['data']
m=[e for e in d if e['user']['username']=='$U']
print(f\"elo={m[0]['eloRating']} wins={m[0]['wins']}\" if m else 'no aparece')")
echo "  en el ranking público: $elo"
# Veredicto explícito (como en C1): ¿se movieron las estadísticas?
python - "$antes" "$despues" <<'PY'
import sys, ast
a, b = (ast.literal_eval(x) for x in sys.argv[1:3])
subio = b["wins"] > a["wins"] or b["wins"] > 0
print("  >>> VULNERABLE: el resultado autodeclarado movió las stats" if subio
      else "  OK: el resultado autodeclarado NO da victorias ni ELO (queda en el historial)")
PY

echo
echo "== C1) ¿El listado de usuarios expone emails? =="
curl -sk "${AUTH[@]}" "$BASE/api/users/" -o /tmp/users_audit.json
python - "$BASE" <<'PY'
import json, sys
try:
    d = json.load(open("/tmp/users_audit.json"))
except Exception as e:
    print("  no se pudo leer la respuesta:", e); raise SystemExit
items = d.get("results", d.get("data", []))
if isinstance(items, dict): items = items.get("results", [])
con_email = [i.get("username") for i in items if i.get("email")]
print(f"  usuarios devueltos: {len(items)} · con email: {len(con_email)}")
print("  >>> VULNERABLE si 'con email' > 0" if con_email else "  OK: no se exponen emails")
PY

echo
echo "== B1) ¿La app de chat funciona? =="
for path in "/api/chat/messages/" "/api/chat/messages/conversation/?user_id=1"; do
  code=$(curl -sk -o /dev/null -w "%{http_code}" "${AUTH[@]}" "$BASE$path")
  printf "  %-46s -> HTTP %s%s\n" "$path" "$code" "$([ "$code" = "500" ] && echo '   >>> ROTO (500)')"
done

echo
echo "== D1) Documentación de la API =="
echo "  (ejecuta en el backend: python manage.py check --deploy | tail -1)"

rm -f /tmp/users_audit.json
