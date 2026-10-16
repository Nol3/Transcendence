"""Prueba end-to-end del póker online: matchmaking, mesa autoritativa, privacidad
de cartas, rechazo de acciones ilegales, bot de reserva y expulsión por inactividad.

Requiere el servidor (daphne) en 127.0.0.1:8011 con:
    POKER_QUEUE_TIMEOUT=3  POKER_TURN_TIMEOUT=6
"""
import asyncio
import json
import sys
import time
import urllib.error
import urllib.request

import websockets

BASE = "http://127.0.0.1:8011"
WS = "ws://127.0.0.1:8011"
ORIGIN = "http://127.0.0.1:8011"
QUEUE_TIMEOUT = 3
TURN_TIMEOUT = 6

results = []


def check(label, ok, detail=""):
    results.append((label, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label} {detail}")


def http(method, path, body=None, token=None):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode() if body is not None else None, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
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
    """WebSocket con un lector en segundo plano que guarda el último estado."""

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

    async def next_message(self, kind, timeout=8.0):
        # Se revisa TODA la lista: 'ready' y 'searching' pueden llegar juntos.
        deadline = time.time() + timeout
        while time.time() < deadline:
            for msg in self.messages:
                if msg.get("type") == kind:
                    return msg
            await asyncio.sleep(0.05)
        return None

    def stop(self):
        if self.task:
            self.task.cancel()


async def connect(url):
    return await websockets.connect(url, origin=ORIGIN)


def inspect_privacy(states):
    """True si en ningún estado se ven cartas ajenas fuera del showdown."""
    for st in states:
        game = st.get("game") or {}
        showdown = bool((game.get("result") or {}).get("showdown"))
        for seat in game.get("seats", []):
            if seat["index"] != st["you"] and seat["hole"] is not None and not showdown:
                return False
    return True


async def play_hand(a, b, max_actions=80):
    """Juega una mano completa con check/call y devuelve (estados vistos, acciones)."""
    seen, actions = [], 0
    for _ in range(max_actions):
        st_a, st_b = a.latest, b.latest
        if st_a is None or st_b is None:
            await asyncio.sleep(0.1)
            continue
        seen.append(st_a)
        seen.append(st_b)
        game = st_a["game"]
        if game["complete"]:
            return seen, actions
        actor = game["actor"]
        if actor is None:
            await asyncio.sleep(0.1)
            continue
        if st_a["you"] == actor:
            view, sock = st_a, a
        elif st_b["you"] == actor:
            view, sock = st_b, b
        else:
            await asyncio.sleep(0.1)
            continue
        opts = view["game"]["legal_actions"]
        if not opts:
            await asyncio.sleep(0.1)
            continue
        pick = next((o for o in opts if o["action"] in ("check", "call")), opts[0])
        marker = (a.latest, b.latest)
        await sock.ws.send(json.dumps({"action": pick["action"], "amount": pick.get("amount")}))
        actions += 1
        for _ in range(60):
            await asyncio.sleep(0.05)
            if a.latest is not marker[0] and b.latest is not marker[1]:
                break
    return seen, actions


async def test_human_vs_human(tok_a, tok_b):
    print("\n  -- 1) Dos humanos: cola, emparejamiento y partida completa --")
    wa = await connect(f"{WS}/ws/poker/matchmaking?token={tok_a}")
    a = Sock(wa, "A"); a.start()
    ready = await a.next_message("ready", 5)
    check("A recibe 'ready' con niveles de apuesta", ready is not None,
          f"-> stakes={list((ready or {}).get('stakes', {}).keys())}")
    searching = await a.next_message("searching", 5)
    check("A entra en cola ('searching')", searching is not None,
          f"-> timeout={(searching or {}).get('queue_timeout')}s")

    wb = await connect(f"{WS}/ws/poker/matchmaking?token={tok_b}")
    b = Sock(wb, "B"); b.start()
    match_a = await a.next_message("match_found", 8)
    match_b = await b.next_message("match_found", 8)
    check("emparejamiento humano-humano",
          bool(match_a and match_b) and match_a["table_id"] == match_b["table_id"],
          f"-> {match_a.get('message') if match_a else None}")
    table = match_a["table_id"]
    a.stop(); b.stop()
    await wa.close(); await wb.close()

    ta = Sock(await connect(f"{WS}/ws/poker/table/{table}?token={tok_a}"), "A/table"); ta.start()
    tb = Sock(await connect(f"{WS}/ws/poker/table/{table}?token={tok_b}"), "B/table"); tb.start()
    st_a = await ta.wait_for(lambda s: True, 5)
    st_b = await tb.wait_for(lambda s: True, 5)
    check("la mesa entrega estado a los dos", bool(st_a and st_b))
    if st_a:
        game = st_a["game"]
        check("A ve SUS cartas y no las del rival",
              game["seats"][st_a["you"]]["hole"] is not None
              and all(s["hole"] is None for s in game["seats"] if s["index"] != st_a["you"]),
              f"-> A={game['seats'][st_a['you']]['hole']}")
        check("el servidor marca de quién es el turno", game["actor"] is not None,
              f"-> actor={game['actor']} calle={game['street']} bote={game['pot']}")

        wrong = tb if game["actor"] == st_a["you"] else ta
        marker = len(wrong.messages)
        await wrong.ws.send(json.dumps({"action": "call"}))
        err = None
        for _ in range(60):
            await asyncio.sleep(0.05)
            err = next((m for m in wrong.messages[marker:] if m.get("type") == "error"), None)
            if err:
                break
        check("acción fuera de turno rechazada", err is not None, f"-> {(err or {}).get('error')}")

        actor_sock = ta if game["actor"] == st_a["you"] else tb
        marker = len(actor_sock.messages)
        await actor_sock.ws.send(json.dumps({"action": "raise", "amount": 11}))
        err2 = None
        for _ in range(60):
            await asyncio.sleep(0.05)
            err2 = next((m for m in actor_sock.messages[marker:] if m.get("type") == "error"), None)
            if err2:
                break
        check("subida por debajo del mínimo rechazada", err2 is not None,
              f"-> {(err2 or {}).get('error')}")

    seen, actions = await play_hand(ta, tb)
    check("la mano se juega hasta el final con acciones reales", actions >= 6,
          f"-> {actions} acciones enviadas")
    check("nunca se filtraron las cartas del rival",
          inspect_privacy(seen), f"-> {len(seen)} estados revisados")
    final = ta.latest
    game = final["game"]
    res = game["result"]
    check("showdown con bote repartido", bool(res and res["pots"] and res["showdown"]),
          f"-> bote={res['total']} showdown={res['showdown']}")
    check("se revelan las cartas al llegar al showdown", len(res["revealed"]) == 2,
          f"-> {res['revealed']}")
    check("el ganador tiene la mejor mano registrada",
          all(w.get("hand") for p in res["pots"] for w in p["winners"]),
          f"-> {[w['hand'] for p in res['pots'] for w in p['winners']]}")
    stacks = [s["stack"] for s in game["seats"]]
    check("las fichas cuadran (2000 en total)", sum(stacks) == 2000, f"-> stacks={stacks}")
    ta.stop(); tb.stop()
    await ta.ws.close(); await tb.ws.close()


async def test_bot_fallback(tok_c):
    print("\n  -- 2) Un solo humano: tras el tiempo de espera entra un bot --")
    wc = await connect(f"{WS}/ws/poker/matchmaking?token={tok_c}")
    c = Sock(wc, "C"); c.start()
    await c.next_message("ready", 5)
    await c.next_message("searching", 5)
    t0 = time.time()
    match = await c.next_message("match_found", QUEUE_TIMEOUT + 8)
    check("tras el timeout se asigna un bot",
          bool(match) and "Bot" in (match.get("opponent") or ""),
          f"-> {match.get('message') if match else None} (esperó {time.time() - t0:.1f}s)")
    c.stop(); await wc.close()

    tc = Sock(await connect(f"{WS}/ws/poker/table/{match['table_id']}?token={tok_c}"), "C/table")
    tc.start()
    st = await tc.wait_for(lambda s: True, 5)
    check("la mesa del bot entrega estado", bool(st))
    check("el rival está marcado como bot",
          bool(st) and any(s["is_bot"] for s in st["game"]["seats"]))

    bot_played = False
    deadline = time.time() + 15
    while time.time() < deadline and not bot_played:
        st = tc.latest
        if st and st["game"]:
            bot_played = any(ev.get("event") == "action" and ev.get("seat") != st["you"]
                             for ev in st["game"]["history"])
        await asyncio.sleep(0.2)
    check("el bot actúa solo (sin intervención humana)", bot_played)

    timed_out = False
    deadline = time.time() + TURN_TIMEOUT + 10
    while time.time() < deadline and not timed_out:
        st = tc.latest
        if st and any(ev.get("event") == "timeout" for ev in st.get("log", [])):
            timed_out = True
        await asyncio.sleep(0.2)
    check("la inactividad se resuelve sola (check/fold automático)", timed_out)

    played = 0
    for _ in range(40):
        st = tc.latest
        if not st or not st["game"] or st["game"]["complete"]:
            await asyncio.sleep(0.2)
            continue
        if st["game"]["actor"] == st["you"]:
            opts = st["game"]["legal_actions"]
            if opts:
                pick = next((o for o in opts if o["action"] in ("check", "call")), opts[0])
                await tc.ws.send(json.dumps({"action": pick["action"],
                                             "amount": pick.get("amount")}))
                played += 1
        await asyncio.sleep(0.3)
    check("el humano puede seguir jugando contra el bot", played > 0, f"-> {played} acciones")
    tc.stop(); await tc.ws.close()


async def main():
    print("=== Póker online: prueba end-to-end por WebSocket ===")
    st, _ = http("GET", "/api/health/")
    check("servidor vivo", st == 200, f"-> {st}")
    tok_a, _ = register("poker_a")
    tok_b, _ = register("poker_b")
    tok_c, _ = register("poker_c")

    await test_human_vs_human(tok_a, tok_b)
    await test_bot_fallback(tok_c)

    print("\n================ RESUMEN ================")
    fails = [r for r in results if not r[1]]
    print(f"{len(results) - len(fails)}/{len(results)} comprobaciones OK")
    for label, _, detail in fails:
        print(f"  FALLO: {label} {detail}")
    sys.exit(0 if not fails else 1)


asyncio.run(main())
