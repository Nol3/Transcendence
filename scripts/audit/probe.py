"""Sonda end-to-end del backend: REST que usa el lobby + WebSockets de matchmaking/salas."""
import asyncio, json, sys, time
import urllib.request, urllib.error
import websockets

BASE = "http://127.0.0.1:8011"
WS = "ws://127.0.0.1:8011"
results = []


def http(method, path, body=None, token=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read().decode()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw[:200]
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def check(label, ok, detail=""):
    results.append((label, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label} {detail}")


# ── REST ──────────────────────────────────────────────────────────────────
st, _ = http("GET", "/api/health/")
check("GET /api/health/", st == 200, f"-> {st}")

stamp = str(int(time.time()))
tokens = {}
for i in (1, 2):
    st, body = http("POST", "/api/auth/register/", {
        "username": f"audit_p{i}_{stamp}",
        "email": f"audit_p{i}_{stamp}@example.com",
        "password": "Zx9!pqLmn42",
    })
    tok = (body or {}).get("data", {}).get("tokens", {}).get("accessToken") if isinstance(body, dict) else None
    tokens[i] = tok
    check(f"POST /api/auth/register/ (jugador {i})", st == 201 and bool(tok), f"-> {st}")

tok = tokens[1]
st, body = http("POST", "/api/games/create_game/", {}, tok)
game_id = body.get("id") if isinstance(body, dict) else None
p2 = (body or {}).get("player2", {}) if isinstance(body, dict) else {}
check("POST /api/games/create_game/ (crea partida vs rival)", st == 201 and game_id is not None,
      f"-> {st} player2={p2.get('username') if isinstance(p2, dict) else p2}")

# Endpoints que el lobby del frontend llama de verdad
for method, path in [("GET", "/api/rooms/"), ("POST", "/api/matchmaking/start/"),
                     ("POST", "/api/matchmaking/cancel/")]:
    st, body = http(method, path, {} if method == "POST" else None, tok)
    check(f"{method} {path}  (usado por RoomService del front)", st not in (404, None),
          f"-> HTTP {st} {str(body)[:90]}")

if game_id:
    st, body = http("POST", f"/api/games/{game_id}/finish/",
                    {"winner": f"audit_p1_{stamp}", "player1_score": 420, "player2_score": 100}, tok)
    check("POST /api/games/<id>/finish/ (ELO + stats)", st == 200, f"-> {st}")

st, body = http("GET", "/api/users/me/stats/", None, tok)
check("GET /api/users/me/stats/", st == 200, f"-> {st} {str(body)[:120]}")


# ── WebSockets ────────────────────────────────────────────────────────────
async def ws_probe():
    print("\n  -- WebSocket matchmaking: 2 clientes concurrentes --")
    ORIGIN = "http://127.0.0.1:8011"
    async with websockets.connect(f"{WS}/ws/matchmaking?token={tok}", origin=ORIGIN) as a:
        m1 = json.loads(await asyncio.wait_for(a.recv(), 5))
        check("cliente A recibe 'searching'", m1.get("type") == "searching", f"-> {m1}")

        async with websockets.connect(f"{WS}/ws/matchmaking?token={tok}", origin=ORIGIN) as b:
            ma = json.loads(await asyncio.wait_for(a.recv(), 5))
            mb = json.loads(await asyncio.wait_for(b.recv(), 5))
            same = ma.get("roomId") and ma.get("roomId") == mb.get("roomId")
            check("emparejamiento inmediato: ambos reciben el MISMO roomId", bool(same),
                  f"-> A={ma} B={mb}")
            check("el backend NO espera timeout para ofrecer un bot",
                  ma.get("type") == "match_found", f"-> type={ma.get('type')}")

            # ¿La sala transmite sin autenticar?
            room = ma["roomId"]
            async with websockets.connect(f"{WS}/ws/rooms/{room}", origin=ORIGIN) as anon:
                first = json.loads(await asyncio.wait_for(anon.recv(), 5))
                check("WS /ws/rooms/<id> SIN token: conecta igualmente (sin auth)",
                      first.get("type") == "room_update", f"-> {first}")
                await anon.send(json.dumps({"room": {"id": room, "status": "INYECTADO"}}))
                got = json.loads(await asyncio.wait_for(anon.recv(), 5))
                check("WS /ws/rooms/<id>: el cliente inyecta estado que se difunde",
                      got.get("room", {}).get("status") == "INYECTADO", f"-> {got}")

            # ¿Alguien recibe el estado de la partida por la sala?
            try:
                await asyncio.wait_for(a.recv(), 1.5)
                check("la sala entrega estado de partida al jugador", True)
            except asyncio.TimeoutError:
                check("la sala entrega estado de partida al jugador", False,
                      "-> nunca llega ningún estado de juego (la partida no existe en el servidor)")


asyncio.run(ws_probe())

print("\n================ RESUMEN ================")
fails = [r for r in results if not r[1]]
print(f"{len(results) - len(fails)}/{len(results)} comprobaciones OK")
for label, _, detail in fails:
    print(f"  FALLO: {label} {detail}")
sys.exit(0)
