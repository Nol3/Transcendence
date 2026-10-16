"""Imprime el transcript de una mano real jugada por el motor (dos bots)."""
import os, random, sys
sys.path.insert(0, "/mnt/c/Users/aleja/Desktop/github/Transcendence/backend")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from apps.poker.bots import decide
from apps.poker.engine import STREET_NAMES, Hand, evaluate

STREETS = {0: "PREFLOP", 1: "FLOP", 2: "TURN", 3: "RIVER"}
NAMES = {0: "Ana", 1: "Bot Málaga"}


def play(seed: int):
    rng = random.Random(seed)
    hand = Hand(stacks=[1000, 1000], button=0, small_blind=5, big_blind=10,
                names=[NAMES[0], NAMES[1]], bots=[1], rng=rng).start()
    print(f"=== Mano (semilla {seed}) — ciegas 5/10, botón: {NAMES[0]} ===")
    print("Cartas privadas: " + "  ".join(
        f"{NAMES[s.index]}={[str(c) for c in s.hole]}" for s in hand.seats))
    street = None
    guard = 0
    while not hand.complete and guard < 200:
        guard += 1
        if hand.street != street:
            street = hand.street
            board = " ".join(str(c) for c in hand.board) or "-"
            print(f"\n[{STREETS[street]}] tablero: {board}   bote: {hand.pot_total}")
        idx = hand.actor
        action, amount = decide(hand, idx, rng)
        opts = {o["action"]: o for o in hand.legal_actions(idx)}
        detail = f" -> {amount}" if amount else ""
        if action in ("call",) and "amount" in opts:
            detail = f" -> {opts['amount']['amount']}"
        hand.act(idx, action, amount)
        print(f"   {NAMES[idx]:<12} {action.upper()}{detail}")

    res = hand.result
    print(f"\nTABLERO FINAL: {' '.join(res['board'])}")
    if res["showdown"]:
        print("SHOWDOWN:")
        for i, cards in res["revealed"].items():
            print(f"   {NAMES[i]:<12} {cards}  ->  {res['hands'][i]['name']}")
    else:
        print("Nadie mostró cartas: todos se retiraron menos uno.")
    print("BOTE REPARTIDO:")
    for pot in res["pots"]:
        for w in pot["winners"]:
            print(f"   {w['name']:<12} gana {w['amount']:>5}  ({w['hand'] or 'sin showdown'})")
    print(f"STACKS FINALES: {NAMES[0]}={hand.seats[0].stack}  {NAMES[1]}={hand.seats[1].stack}")
    print(f"SUMA: {sum(s.stack for s in hand.seats)} (debe ser 2000)")


for s in (7, 21):
    play(s)
    print()
