"""Reglas del Culo (Presidente), en el servidor.

Esto es un port fiel del motor que ya estaba probado en el front
(`front/src/app/core/games/culo/culo-engine.ts`). En cuanto la partida es online las
reglas **tienen** que vivir aquí: si las decidiera el navegador, cualquiera podría
jugarse las cartas que quisiera desde la consola.

Lo esencial del juego, tal y como está escrito en las normas:
  - Una jugada son **una o varias cartas del mismo valor**.
  - Para responder hay que jugar **exactamente la misma cantidad** de cartas y de
    **valor superior**. Ni una menos, ni una más, ni de otro valor.
  - **Se puede pasar aunque tengas jugada**: pasar es una decisión, no una obligación.
  - La baza sigue hasta que todos los demás pasan; el último que jugó válido se lleva
    las cartas y abre la siguiente.
  - El primero que se queda sin cartas es el **Presidente** y el último el **Culo**, y
    en la ronda siguiente intercambian cartas.

Las funciones que **deciden** (valor, jugada, respuestas legales, roles, intercambio)
son puras; las que **avanzan** la partida modifican el estado que se les pasa, que es
uno por sala y solo lo toca su consumidor.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

# Palos, valores y reparto: comunes a todos los juegos (`apps/baraja.py`).
# Aquí solo queda **lo que es del Culo**: su orden de fuerza.
from ..baraja import RANKS, SUITS, Card, build_deck, deal, shuffle  # noqa: F401  (se reexportan)

ROLES = ("presidente", "vicepresidente", "neutro", "viceculo", "culo")


def strength(card: Card) -> int:
    """Fuerza de una carta dentro del juego.

    De menor a mayor: 2, 3, 4, 5, 6, 7, Sota, Caballo, Rey, As… y por encima de todas,
    **el 5 de oros**. Ese 5 vale más que cualquier otra, así que no se puede jugar junto
    a otros cincos: no comparten valor.
    """
    if card.rank == 5 and card.suit == "o":
        return 12
    if card.rank == 1:
        return 11
    if card.rank == 12:
        return 10
    if card.rank == 11:
        return 9
    if card.rank == 10:
        return 8
    return card.rank


def sort_hand(hand: list[Card]) -> list[Card]:
    return sorted(hand, key=lambda c: (-strength(c), c.suit))


# ── Jugadas ──────────────────────────────────────────────────────────────────

def combo_of(cards: list[Card]) -> int | None:
    """Fuerza de la jugada si todas las cartas son del mismo valor; `None` si no."""
    if not cards:
        return None
    valor = strength(cards[0])
    return valor if all(strength(c) == valor for c in cards) else None


def can_beat(play_count: int, play_strength: int, table: Trick | None) -> bool:
    """¿Una jugada responde a lo que hay en la mesa? Misma cantidad y más valor."""
    if table is None:
        return True
    return play_count == table.count and play_strength > table.strength


def legal_combos(state: GameState, player_id: int) -> list[list[Card]]:
    """Todas las jugadas que puede hacer un jugador ahora mismo.

    Con mesa: las que tienen exactamente su cantidad y más valor. Sin mesa (abriendo):
    cualquier cantidad de cualquier valor que tenga en la mano.
    """
    jugador = state.players[player_id]
    por_valor: dict[int, list[Card]] = {}
    for carta in jugador.hand:
        por_valor.setdefault(strength(carta), []).append(carta)

    jugadas: list[list[Card]] = []
    for valor, cartas in por_valor.items():
        if state.table is not None:
            if len(cartas) >= state.table.count and valor > state.table.strength:
                jugadas.append(cartas[: state.table.count])
        else:
            for n in range(1, len(cartas) + 1):
                jugadas.append(cartas[:n])
    return jugadas


# ── Estado ───────────────────────────────────────────────────────────────────

@dataclass
class Player:
    id: int
    name: str
    is_bot: bool
    hand: list[Card] = field(default_factory=list)
    role: str | None = None
    place: int | None = None
    connected: bool = True


@dataclass
class Trick:
    cards: list[Card]
    by: int
    strength: int
    count: int


@dataclass
class GameState:
    players: list[Player]
    turn: int = 0
    table: Trick | None = None
    passed: list[int] = field(default_factory=list)
    round: int = 1
    decks: int = 1
    events: list[dict] = field(default_factory=list)
    phase: str = "playing"  # playing | round-end


def new_game(names: list[str], bots: list[bool], decks: int = 1,
             round_number: int = 1, rng: random.Random | None = None) -> GameState:
    rng = rng or random
    manos = deal(shuffle(build_deck(decks), rng), len(names))
    return GameState(
        players=[
            Player(id=i, name=name, is_bot=bots[i], hand=sort_hand(manos[i]))
            for i, name in enumerate(names)
        ],
        # La primera ronda empieza uno cualquiera; a partir de la segunda abre el Presidente.
        turn=rng.randrange(len(names)),
        round=round_number,
        decks=decks,
    )


# ── Jugar ────────────────────────────────────────────────────────────────────

def can_play(state: GameState, player_id: int, cards: list[Card]) -> bool:
    if state.phase != "playing" or state.turn != player_id:
        return False
    if not cards:
        return False
    # La misma carta no se puede jugar dos veces: si no se comprueba, dos copias del
    # mismo id pasarían por «pareja» y el jugador se descartaría de una sola carta.
    ids = [c.id for c in cards]
    if len(set(ids)) != len(ids):
        return False
    jugador = state.players[player_id]
    suyas = {c.id for c in jugador.hand}
    if not all(i in suyas for i in ids):
        return False
    valor = combo_of(cards)
    return valor is not None and can_beat(len(cards), valor, state.table)


def play(state: GameState, player_id: int, cards: list[Card]) -> bool:
    """Juega si la jugada es legal. Devuelve si se ha jugado."""
    if not can_play(state, player_id, cards):
        return False
    valor = combo_of(cards)
    assert valor is not None
    ids = {c.id for c in cards}
    jugador = state.players[player_id]
    jugador.hand = [c for c in jugador.hand if c.id not in ids]

    state.table = Trick(cards=list(cards), by=player_id, strength=valor, count=len(cards))
    # Quien juega vuelve a estar dentro: si había pasado, su jugada lo reengancha.
    state.passed = [p for p in state.passed if p != player_id]
    state.events.append({"kind": "play", "player": player_id,
                         "count": len(cards), "strength": valor})
    _after_action(state, player_id)
    return True


def do_pass(state: GameState, player_id: int) -> bool:
    if state.phase != "playing" or state.turn != player_id:
        return False
    if player_id not in state.passed:
        state.passed.append(player_id)
    state.events.append({"kind": "pass", "player": player_id})
    _after_action(state, player_id)
    return True


def _after_action(state: GameState, actor: int) -> None:
    """Decide a quién le toca, si se cierra la baza o si se acaba la ronda."""
    if not state.players[actor].hand and state.players[actor].place is None:
        _mark_out(state, actor)

    con_cartas = [p for p in state.players if p.hand]
    if len(con_cartas) <= 1:
        if con_cartas:
            _mark_out(state, con_cartas[0].id)
        assign_roles(state)
        return

    siguiente = _next_to_act(state)
    if siguiente == -1 or (state.table is not None and siguiente == state.table.by):
        _close_trick(state)
        return
    state.turn = siguiente


def _mark_out(state: GameState, player_id: int) -> None:
    puesto = sum(1 for p in state.players if p.place is not None) + 1
    state.players[player_id].place = puesto
    state.events.append({"kind": "out", "player": player_id, "place": puesto})


def _next_to_act(state: GameState) -> int:
    """Siguiente jugador que puede actuar: con cartas y sin haber pasado en esta baza."""
    n = len(state.players)
    for i in range(1, n + 1):
        idx = (state.turn + i) % n
        p = state.players[idx]
        if not p.hand or idx in state.passed:
            continue
        return idx
    return -1


def _next_active_after(state: GameState, from_id: int) -> int:
    n = len(state.players)
    for i in range(1, n + 1):
        idx = (from_id + i) % n
        if state.players[idx].hand:
            return idx
    return from_id


def _close_trick(state: GameState) -> None:
    ganador = state.table.by if state.table else state.turn
    state.turn = ganador if state.players[ganador].hand else _next_active_after(state, ganador)
    state.table = None
    state.passed = []
    state.events.append({"kind": "trick", "player": ganador})


# ── Fin de ronda: puestos y roles ────────────────────────────────────────────

def assign_roles(state: GameState) -> None:
    """Reparte los roles según el orden en que cada uno se quedó sin cartas.

    Con **3 jugadores** no hay vicepresidente ni viceculo (el segundo sería a la vez
    vicepresidente y viceculo): quedan Presidente, un neutro y Culo. Con 4 o más, el
    segundo es Vicepresidente y el penúltimo Viceculo.
    """
    n = len(state.players)
    por_puesto = sorted(state.players, key=lambda p: p.place if p.place is not None else 99)

    roles: dict[int, str] = {}
    if por_puesto:
        roles[por_puesto[0].id] = "presidente"
        roles[por_puesto[-1].id] = "culo"
    if n >= 4:
        roles[por_puesto[1].id] = "vicepresidente"
        roles[por_puesto[-2].id] = "viceculo"
    for p in state.players:
        p.role = roles.get(p.id, "neutro")
    state.phase = "round-end"


def standings(state: GameState) -> list[Player]:
    return sorted(state.players, key=lambda p: p.place if p.place is not None else 99)


# ── Intercambio entre rondas ─────────────────────────────────────────────────

def exchange_swaps(state: GameState) -> list[dict]:
    """Intercambio antes de la siguiente ronda.

    El Culo le da sus **2 mejores** al Presidente, que devuelve sus **2 peores**; el
    Viceculo le da su **mejor** al Vicepresidente, que devuelve su **peor**. Se calcula
    aparte de aplicarlo para poder enseñarlo antes de hacerlo.
    """
    por_rol = {p.role: p for p in state.players}
    presidente, culo = por_rol.get("presidente"), por_rol.get("culo")
    vicepresidente, viceculo = por_rol.get("vicepresidente"), por_rol.get("viceculo")

    swaps: list[dict] = []
    if presidente and culo:
        swaps.append({"from": culo.id, "to": presidente.id,
                      "cards": sort_hand(culo.hand)[:2]})
        swaps.append({"from": presidente.id, "to": culo.id,
                      "cards": sort_hand(presidente.hand)[-2:]})
    if vicepresidente and viceculo:
        swaps.append({"from": viceculo.id, "to": vicepresidente.id,
                      "cards": sort_hand(viceculo.hand)[:1]})
        swaps.append({"from": vicepresidente.id, "to": viceculo.id,
                      "cards": sort_hand(vicepresidente.hand)[-1:]})
    return [s for s in swaps if s["cards"]]


def apply_swaps(state: GameState, swaps: list[dict]) -> None:
    for swap in swaps:
        ids = {c.id for c in swap["cards"]}
        origen = state.players[swap["from"]]
        destino = state.players[swap["to"]]
        origen.hand = [c for c in origen.hand if c.id not in ids]
        destino.hand = sort_hand(destino.hand + list(swap["cards"]))


def next_round(state: GameState, rng: random.Random | None = None) -> None:
    """Arranca la ronda siguiente conservando nombres, bots y roles."""
    rng = rng or random
    manos = deal(shuffle(build_deck(state.decks), rng), len(state.players))
    presidente = next((p for p in state.players if p.role == "presidente"), None)
    for i, p in enumerate(state.players):
        p.hand = sort_hand(manos[i])
        p.place = None
    state.turn = presidente.id if presidente else rng.randrange(len(state.players))
    state.table = None
    state.passed = []
    state.round += 1
    state.events = []
    state.phase = "playing"


# ── Vista por jugador ────────────────────────────────────────────────────────

def state_for(state: GameState, viewer_id: int | None) -> dict:
    """Lo que puede ver un jugador: su mano y, de los demás, solo cuántas cartas tienen.

    `viewer_id` es el **asiento** en la partida (0, 1, 2…), no el id de usuario: la sala
    es la que traduce. Es la razón de que el juego sea online de verdad: las cartas
    ajenas **nunca** salen del servidor hasta que toca enseñarlas.
    """
    return {
        "players": [
            {
                "id": p.id,
                "name": p.name,
                "isBot": p.is_bot,
                "handCount": len(p.hand),
                "role": p.role,
                "place": p.place,
                "connected": p.connected,
                "hand": [c.to_dict() for c in p.hand] if p.id == viewer_id else [],
            }
            for p in state.players
        ],
        "turn": state.turn,
        "table": (
            {
                "cards": [c.to_dict() for c in state.table.cards],
                "by": state.table.by,
                "strength": state.table.strength,
                "count": state.table.count,
            }
            if state.table
            else None
        ),
        "passed": list(state.passed),
        "round": state.round,
        "decks": state.decks,
        "events": list(state.events),
        "phase": state.phase,
    }
