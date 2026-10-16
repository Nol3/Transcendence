"""Verifica la mesa de póker de un match de torneo contra el stack desplegado.

Recorre el camino completo del 5.1:

    registrar 2 jugadores → torneo de 2 → bracket → abrir la mesa del match
    → entrar los dos por WebSocket → la mano se reparte SOLO al estar los dos
    → cada uno ve sus cartas y solo las suyas → las acciones se aceptan

Uso:  python probe_tournament_table.py [https://localhost:8443]
"""
import asyncio
import json
import ssl
import sys
import time
import urllib.error
import urllib.request

import websockets

BASE = sys.argv[1] if len(sys.argv) > 1 else "https://localhost:8443"
WS = BASE.replace("https://", "wss://").replace("http://", "ws://")
ORIGIN = BASE
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

results = []


def check(label, ok, detail=""):
    results.append((label, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label} {detail}")


def http(method, path, body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=20, context=SSL_CTX) as r:
            return r.status, json.loads(r.read().decode() or "null")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or "null")
        except Exception:
            return e.code, None


def register(name):
    stamp = str(int(time.time() * 1000))
    st, body = http("POST", "/api/auth/register/", {
        "username": f"{name}_{stamp}", "email": f"{name}_{stamp}@example.com",
        "password": "Zx9!pqLmn42"})
    assert st == 201, (st, body)
    return body["data"]["tokens"]["accessToken"], body["data"]["user"]["username"], \
        body["data"]["user"]["id"]


class Sock:
    """WebSocket con lector en segundo plano que guarda el último estado."""

    def __init__(self, ws, name):
        self.ws, self.name = ws, name
        self.latest = None
        self.messages = []
        self.task = None

    def start(self):
        self.task = asyncio.create_task(self._reader())

    async def _reader(self):
        try:
            async for raw in self.ws:
                msg = json.loads(raw)
                self.messages.append(msg)
                if msg.get("type") == "table_state":
                    self.latest = msg
        except Exception:
            pass

    async def wait_for(self, predicate, timeout=8.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.latest is not None and predicate(self.latest):
                return self.latest
            await asyncio.sleep(0.05)
        return self.latest

    def stop(self):
        if self.task:
            self.task.cancel()


async def main():
    print(f"stack: {BASE}")
    # El backend exige mínimo 4 jugadores por torneo: se registran 4 y se juega
    # el primer match del bracket con sus dos jugadores.
    cuentas = {}
    for i in range(4):
        tok, nombre, uid = register(f"tt{i}")
        cuentas[uid] = (tok, nombre)
    print("jugadores: " + ", ".join(f"{n} (#{i})" for i, (_, n) in cuentas.items()))

    primero = next(iter(cuentas.values()))
    st, tor = http("POST", "/api/tournament/create_tournament/",
                   {"name": "Probe 5.1", "max_players": 4}, primero[0])
    check("se crea el torneo", st == 201, f"HTTP {st}")
    tid = tor["id"]
    for i, (tok, _) in cuentas.items():
        if tok == primero[0]:
            continue          # el creador ya está dentro desde la creación
        st_join, _ = http("POST", f"/api/tournament/{tid}/join/", {}, tok)
        check(f"se une el jugador #{i}", st_join in (200, 201), f"HTTP {st_join}")

    st, detalle = http("GET", f"/api/tournament/{tid}/", token=primero[0])
    rondas = detalle.get("rounds") or []
    check("el bracket se genera al llenarse",
          len(rondas) == 1 and len(rondas[0]["matches"]) == 2,
          f"rondas={len(rondas)} matches={len(rondas[0]['matches']) if rondas else 0}")
    match = rondas[0]["matches"][0]
    check("el match tiene los dos jugadores",
          match["player1"] is not None and match["player2"] is not None,
          f"{match['player1']['username']} vs {match['player2']['username']}")

    tok_a, name_a = cuentas[match["player1"]["id"]]
    tok_b, name_b = cuentas[match["player2"]["id"]]
    id_a, id_b = match["player1"]["id"], match["player2"]["id"]

    # ── Abrir la mesa del match (los dos deben acabar en la misma) ───────────
    st_a, mesa_a = http("POST", f"/api/tournament/{tid}/matches/{match['id']}/table/", {}, tok_a)
    check("el jugador abre la mesa", st_a == 200, f"HTTP {st_a}")
    st_b, mesa_b = http("POST", f"/api/tournament/{tid}/matches/{match['id']}/table/", {}, tok_b)
    check("el rival abre la MISMA mesa", st_b == 200 and mesa_b["table_id"] == mesa_a["table_id"],
          f"{mesa_a.get('table_id')} / {mesa_b.get('table_id')}")
    check("la mesa trae ciegas y stack",
          mesa_a["small_blind"] == 5 and mesa_a["big_blind"] == 10
          and mesa_a["starting_stack"] == 1000,
          f"{mesa_a['small_blind']}/{mesa_a['big_blind']} stack {mesa_a['starting_stack']}")
    check("la respuesta dice contra quién juegas",
          mesa_a["opponent"]["username"] in (name_a, name_b),
          mesa_a["opponent"]["username"])

    table_id = mesa_a["table_id"]

    # ── Entrar a la mesa ────────────────────────────────────────────────────
    ws_a = await websockets.connect(f"{WS}/ws/poker/table/{table_id}?token={tok_a}",
                                    origin=ORIGIN, ssl=SSL_CTX)
    sock_a = Sock(ws_a, "A")
    sock_a.start()
    await asyncio.sleep(1.0)
    check("con uno solo NO se reparte la mano",
          sock_a.latest is not None and (sock_a.latest.get("game") is None),
          f"hand={'sí' if (sock_a.latest or {}).get('game') else 'no'}")

    ws_b = await websockets.connect(f"{WS}/ws/poker/table/{table_id}?token={tok_b}",
                                    origin=ORIGIN, ssl=SSL_CTX)
    sock_b = Sock(ws_b, "B")
    sock_b.start()

    st_a = await sock_a.wait_for(lambda s: s.get("game") is not None, timeout=8)
    st_b = await sock_b.wait_for(lambda s: s.get("game") is not None, timeout=8)
    check("al entrar los dos, la mano se reparte sola",
          st_a.get("game") is not None and st_b.get("game") is not None)

    def hole_of(state):
        seat = next((s for s in state["game"]["seats"] if s["index"] == state["you"]), None)
        return seat["hole"] if seat else None

    check("cada uno ve sus 2 cartas",
          len(hole_of(st_a) or []) == 2 and len(hole_of(st_b) or []) == 2,
          f"A={hole_of(st_a)} B={hole_of(st_b)}")
    check("no veo las cartas del rival",
          all(s["hole"] is None for s in st_a["game"]["seats"] if s["index"] != st_a["you"]))
    check("los dos asientos son los dos jugadores",
          {s["name"] for s in st_a["game"]["seats"]} == {name_a, name_b},
          str([s["name"] for s in st_a["game"]["seats"]]))
    check("no hay bots en la mesa",
          all(not s.get("is_bot") for s in st_a["game"]["seats"]))

    # ── Una acción real del que tiene el turno ──────────────────────────────
    actor = "A" if st_a["game"]["actor"] == st_a["you"] else "B"
    estado = st_a if actor == "A" else st_b
    ws = ws_a if actor == "A" else ws_b
    opciones = [o["action"] for o in (estado["game"].get("legal_actions") or [])]
    jugada = "check" if "check" in opciones else ("call" if "call" in opciones else "fold")
    await ws.send(json.dumps({"action": jugada}))
    objetivo = (lambda s: s["game"]["actor"] != s["you"]) if actor == "A" else \
               (lambda s: s["game"]["actor"] != s["you"])
    sock = sock_a if actor == "A" else sock_b
    antes = sock.latest["game"].get("pot", 0)
    nuevo = await sock.wait_for(lambda s: s["game"] is not None and
                                (s["game"]["actor"] != s["you"] or s["game"].get("pot", 0) != antes),
                                timeout=8)
    check(f"la acción del que tiene el turno ({actor}: {jugada}) se aplica",
          nuevo is not None and nuevo["game"] is not None,
          f"actor ahora = {nuevo['game']['actor'] if nuevo else '?'}")

    # ── Acción ilegal: el que NO tiene el turno no puede mover ──────────────
    # Tras la jugada anterior el turno pasó al otro asiento, así que se intenta
    # actuar desde el que ya no le toca (y con una subida imposible).
    fuera = next((s for s in (sock_a, sock_b)
                  if s.latest and s.latest.get("game")
                  and s.latest["game"]["actor"] != s.latest["you"]), None)
    ws_fuera = ws_a if fuera is sock_a else ws_b
    if fuera is not None:
        antes_err = len([m for m in fuera.messages if m.get("type") == "error"])
        await ws_fuera.send(json.dumps({"action": "raise", "amount": 999999}))
        await asyncio.sleep(0.8)
        errores = [m for m in fuera.messages if m.get("type") == "error"]
        check("una acción fuera de turno se rechaza", len(errores) > antes_err,
              errores[-1]["error"] if errores else "sin respuesta")
    else:
        check("una acción fuera de turno se rechaza", False, "no encontré a quién no le tocaba")

    sock_a.stop()
    sock_b.stop()
    await ws_a.close()
    await ws_b.close()

    ok = sum(1 for _, o, _ in results if o)
    print(f"\n================ {ok}/{len(results)} comprobaciones OK ================")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
