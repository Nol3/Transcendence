"""Verifica espectadores y chat de mesa contra el stack desplegado (5.4).

    A y B juegan (cola de 2) → C entra a mirar la misma mesa
      · C recibe la vista sin asiento y NO ve cartas ajenas
      · C no puede actuar (el servidor lo rechaza)
      · C escribe en el chat y A/B lo ven; A escribe y C lo ve

Uso:  python probe_spectators.py [https://localhost:8443]
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

    async def wait_for(self, kind, timeout=20.0, predicate=None):
        deadline = time.time() + timeout
        while time.time() < deadline:
            for m in self.messages:
                if m.get("type") == kind and (predicate is None or predicate(m)):
                    return m
            await asyncio.sleep(0.1)
        return None

    def stop(self):
        if self.task:
            self.task.cancel()


async def main():
    print(f"stack: {BASE}")
    a_tok, a_name = register("esp_a")
    b_tok, b_name = register("esp_b")
    c_tok, c_name = register("esp_c")
    print(f"A={a_name}  B={b_name}  C(espectador)={c_name}")

    # ── A y B se emparejan y entran a la mesa ───────────────────────────────
    qa = await websockets.connect(f"{WS}/ws/poker/matchmaking?token={a_tok}&size=2",
                                  origin=ORIGIN, ssl=SSL_CTX)
    sa = Sock(qa, a_name)
    sa.start()
    qb = await websockets.connect(f"{WS}/ws/poker/matchmaking?token={b_tok}&size=2",
                                  origin=ORIGIN, ssl=SSL_CTX)
    sb = Sock(qb, b_name)
    sb.start()

    aviso = await sa.wait_for("match_found", timeout=30)
    check("los dos jugadores se emparejan", aviso is not None,
          aviso.get("table_id") if aviso else "sin mesa")
    if aviso is None:
        return 1
    table_id = aviso["table_id"]

    ta = await websockets.connect(f"{WS}/ws/poker/table/{table_id}?token={a_tok}",
                                  origin=ORIGIN, ssl=SSL_CTX)
    sa2 = Sock(ta, a_name)
    sa2.start()
    tb = await websockets.connect(f"{WS}/ws/poker/table/{table_id}?token={b_tok}",
                                  origin=ORIGIN, ssl=SSL_CTX)
    sb2 = Sock(tb, b_name)
    sb2.start()
    await asyncio.sleep(2.5)
    check("la partida arranca con los dos",
          sa2.latest is not None and sa2.latest.get("game") is not None)

    # ── C entra a mirar ────────────────────────────────────────────────────
    tc = await websockets.connect(f"{WS}/ws/poker/table/{table_id}?token={c_tok}",
                                  origin=ORIGIN, ssl=SSL_CTX)
    sc = Sock(tc, c_name)
    sc.start()
    estado_c = await sc.wait_for("table_state", timeout=12)
    check("el espectador entra en la mesa", estado_c is not None)
    if estado_c is None:
        return 1
    check("el espectador no tiene asiento", estado_c.get("you") is None,
          f"you={estado_c.get('you')}")
    asientos = (estado_c.get("game") or {}).get("seats") or []
    check("el espectador ve la mesa", len(asientos) == 2,
          str([s["name"] for s in asientos]))
    check("el espectador NO ve ninguna carta",
          all(s.get("hole") is None for s in asientos),
          str([s.get("hole") for s in asientos]))
    check("el espectador ve los stacks", all(s.get("stack") for s in asientos),
          str([s.get("stack") for s in asientos]))

    # ── No puede actuar ────────────────────────────────────────────────────
    await tc.send(json.dumps({"action": "call"}))
    error = await sc.wait_for("error", timeout=8)
    check("una acción del espectador se rechaza", error is not None,
          error.get("error") if error else "sin respuesta")

    # ── Chat de mesa ───────────────────────────────────────────────────────
    await tc.send(json.dumps({"type": "chat", "text": "hola desde la grada"}))
    visto_a = await sa2.wait_for("chat", timeout=8,
                                 predicate=lambda m: "grada" in m.get("text", ""))
    check("los jugadores ven el chat del espectador", visto_a is not None,
          json.dumps(visto_a) if visto_a else "")
    if visto_a:
        check("el chat identifica al espectador",
              visto_a.get("spectator") is True and visto_a.get("from") == c_name,
              f"from={visto_a.get('from')} spectator={visto_a.get('spectator')}")

    await ta.send(json.dumps({"type": "chat", "text": "buena suerte"}))
    visto_c = await sc.wait_for("chat", timeout=8,
                               predicate=lambda m: "suerte" in m.get("text", ""))
    check("el espectador ve el chat de los jugadores", visto_c is not None,
          json.dumps(visto_c) if visto_c else "")

    # ── Tras el showdown, el espectador sí ve lo revelado ──────────────────
    # Se juega la mano a check/call hasta el final. Solo actúa quien, según su
    # estado MÁS RECIENTE, tiene el turno: si se actúa con un estado desfasado el
    # servidor lo rechaza y la mano no avanza.
    for _ in range(80):
        turno = next(
            (s for s in (sa2, sb2)
             if s.latest and s.latest.get("game")
             and not s.latest["game"].get("result")
             and s.latest["game"]["actor"] == s.latest["you"]),
            None,
        )
        if turno is None:
            await asyncio.sleep(0.5)
            continue
        opciones = [o["action"] for o in (turno.latest["game"].get("legal_actions") or [])]
        jugada = "check" if "check" in opciones else "call"
        await turno.ws.send(json.dumps({"action": jugada}))
        await asyncio.sleep(0.7)

    final = await sc.wait_for("table_state", timeout=12,
                              predicate=lambda m: bool((m.get("game") or {}).get("result")))
    if final:
        resultado = final["game"]["result"]
        reveladas = [s.get("hole") for s in final["game"]["seats"]]
        check("en el showdown el espectador ve las cartas reveladas",
              bool(resultado.get("showdown")) and any(reveladas),
              f"showdown={resultado.get('showdown')} cartas={reveladas}")
    else:
        check("en el showdown el espectador ve las cartas reveladas", False,
              "la mano no llegó a terminar en el tiempo del sondeo")

    for s in (sa, sb, sa2, sb2, sc):
        s.stop()

    ok = sum(1 for _, o, _ in results if o)
    print(f"\n================ {ok}/{len(results)} comprobaciones OK ================")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
