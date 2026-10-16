"""Verifica las mesas de 3–6 jugadores contra el stack desplegado.

Dos casos:

1. **Mesa de 3 con tres humanos**: los tres entran en cola con `?size=3` y acaban
   en la misma mesa, sin bots.
2. **Mesa de 6 con un humano**: nadie más aparece, así que tras el tiempo de espera
   la mesa se completa con 5 bots.

Uso:  python probe_multi_seat.py [https://localhost:8443]
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
        return e.code, None


def register(name):
    stamp = str(int(time.time() * 1000))
    st, body = http("POST", "/api/auth/register/", {
        "username": f"{name}_{stamp}", "email": f"{name}_{stamp}@example.com",
        "password": "Zx9!pqLmn42"})
    assert st == 201, (st, body)
    return body["data"]["tokens"]["accessToken"], body["data"]["user"]["username"]


class Sock:
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

    async def wait_for(self, kind, timeout=25.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            for m in self.messages:
                if m.get("type") == kind:
                    return m
            await asyncio.sleep(0.1)
        return None

    def stop(self):
        if self.task:
            self.task.cancel()


async def queue_client(token, size, label):
    url = f"{WS}/ws/poker/matchmaking?token={token}&size={size}"
    ws = await websockets.connect(url, origin=ORIGIN, ssl=SSL_CTX)
    sock = Sock(ws, label)
    sock.start()
    return sock


async def main():
    print(f"stack: {BASE}")

    # ── Caso 1: mesa de 3 con tres humanos ──────────────────────────────────
    jugadores = [register(f"ms{i}") for i in range(3)]
    print("jugadores: " + ", ".join(n for _, n in jugadores))
    socks = [await queue_client(tok, 3, nom) for tok, nom in jugadores]

    avisos = []
    for s in socks:
        avisos.append(await s.wait_for("match_found", timeout=30))
    check("los tres reciben la mesa", all(a is not None for a in avisos),
          str([a and a.get("table_id") for a in avisos]))
    mesas = {a["table_id"] for a in avisos if a}
    check("es la MISMA mesa para los tres", len(mesas) == 1, str(mesas))
    check("la mesa es de 3 asientos", all(a.get("seats") == 3 for a in avisos if a),
          str([a.get("seats") for a in avisos if a]))

    # Los tres entran en la mesa y se reparte una mano a 3
    table_id = mesas.pop()
    table_socks = []
    for (tok, nom) in jugadores:
        ws = await websockets.connect(f"{WS}/ws/poker/table/{table_id}?token={tok}",
                                      origin=ORIGIN, ssl=SSL_CTX)
        s = Sock(ws, nom)
        s.start()
        table_socks.append(s)
    await asyncio.sleep(2.5)
    estados = [s.latest for s in table_socks]
    check("los tres ven la mesa repartida", all(e is not None for e in estados))
    if all(estados):
        e = estados[0]
        asientos = e["game"]["seats"]
        check("hay 3 asientos y ninguno es bot",
              len(asientos) == 3 and not any(a.get("is_bot") for a in asientos),
              str([a["name"] for a in asientos]))
        check("cada uno ve solo sus cartas",
              all(len([a for a in e["game"]["seats"] if a["hole"]]) <= 1 for e in estados))
        check("el actor de la mano es uno de los tres",
              e["game"]["actor"] in [a["index"] for a in asientos])

    for s in table_socks + socks:
        s.stop()

    # ── Caso 2: mesa de 6 con un humano → se completa con bots ──────────────
    tok, nom = register("ms_solo")
    solo = await queue_client(tok, 6, nom)
    buscando = await solo.wait_for("searching", timeout=15)
    check("avisa de que busca 5 jugadores más", buscando is not None,
          buscando.get("message", "")[:60] if buscando else "sin respuesta")

    aviso = await solo.wait_for("match_found", timeout=60)
    check("tras la espera se abre la mesa", aviso is not None,
          str(aviso and aviso.get("table_id")))
    if aviso:
        check("la mesa es de 6", aviso.get("seats") == 6, str(aviso.get("seats")))
        ws = await websockets.connect(f"{WS}/ws/poker/table/{aviso['table_id']}?token={tok}",
                                      origin=ORIGIN, ssl=SSL_CTX)
        s = Sock(ws, nom)
        s.start()
        deadline = time.time() + 12
        while time.time() < deadline and s.latest is None:
            await asyncio.sleep(0.2)
        if s.latest:
            asientos = s.latest["game"]["seats"]
            bots = [a for a in asientos if a.get("is_bot")]
            check("la mesa se llenó con 5 bots", len(asientos) == 6 and len(bots) == 5,
                  f"{len(asientos)} asientos, {len(bots)} bots")
        else:
            check("la mesa se llenó con 5 bots", False, "no llegó el estado")
        s.stop()

    solo.stop()

    ok = sum(1 for _, o, _ in results if o)
    print(f"\n================ {ok}/{len(results)} comprobaciones OK ================")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
