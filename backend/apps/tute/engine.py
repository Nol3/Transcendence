"""Reglas del Tute, en el servidor.

Port fiel del motor que ya está probado en el front (`front/src/app/core/games/tute/`). En cuanto
la partida es online las reglas **tienen** que vivir aquí.

Lo esencial, tal y como está en las normas:
  - **Mientras quede baceta**: solo es obligatorio asistir al **triunfo**, y sin montar.
  - **Terminada la baceta**: obligatorio **asistir, montar y fallar**. Si no tienes del palo y
    tampoco triunfo, vale cualquier carta (contrafallo).
  - Se **canta**: rey y caballo del mismo palo valen 40 si son del triunfo («las cuarenta») y 20 si
    no («las veinte»), solo **después de ganar una baza** y un acuse por baza.
  - Se gana llegando a **101 tantos** o cantando un **tute** (los cuatro reyes o los cuatro
    caballos). La **última baza vale 10** y decide los empates.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from ..baraja import Card, build_deck, deal_some, shuffle
from ..bazas import ganador_de_baza, ordenar_mano, tantos

MIN_JUGADORES = 2
MAX_JUGADORES = 4
TANTOS_PARA_GANAR = 101
DIEZ_ULTIMAS = 10
ACUSE_TRIUNFO = 40
ACUSE_OTRO = 20
PALOS: tuple[str, ...] = ("o", "c", "e", "b")


class TuteError(Exception):
    """Un movimiento imposible, con código corto para que el front lo traduzca."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass
class TutePlayer:
    id: int
    name: str
    is_bot: bool = False
    hand: list[Card] = field(default_factory=list)
    won: list[Card] = field(default_factory=list)
    cantados: int = 0
    connected: bool = True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "isBot": self.is_bot,
            "handCount": len(self.hand),
            "tantos": tantos(self.won),
            "cantados": self.cantados,
            "connected": self.connected,
        }


@dataclass
class TuteState:
    players: list[TutePlayer] = field(default_factory=list)
    baceta: list[Card] = field(default_factory=list)
    trump_card: Card | None = None
    trump_suit: str = "o"
    turn: int = 0
    trick: list[tuple[int, Card]] = field(default_factory=list)
    last_trick: tuple[int, list[tuple[int, Card]]] | None = None
    last_winner: int | None = None
    cantado_en_esta_baza: list[int] = field(default_factory=list)
    scores: list[int] = field(default_factory=list)
    target_tantos: int = TANTOS_PARA_GANAR
    events: list[dict[str, Any]] = field(default_factory=list)
    phase: str = "playing"  # playing | game-end | match-end
    winner: int | None = None


def cartas_por_jugador(jugadores: int) -> int:
    if jugadores <= 2:
        return 8
    if jugadores == 3:
        return 13  # el «tute arrastrado»
    return 10  # cuatro, por parejas


def new_game(
    names: list[str],
    bots: list[bool] | None = None,
    scores: list[int] | None = None,
    dealer: int | None = None,
    rng: random.Random | None = None,
) -> TuteState:
    if not MIN_JUGADORES <= len(names) <= MAX_JUGADORES:
        raise TuteError(
            "players", f"el tute se juega entre {MIN_JUGADORES} y {MAX_JUGADORES} jugadores"
        )
    mazo = shuffle(build_deck(1), rng)
    manos, resto = deal_some(mazo, len(names), cartas_por_jugador(len(names)))
    # La carta que pinta queda debajo de la baceta: es la última que se roba.
    trump_card = resto[0] if resto else None
    repartidor = len(names) - 1 if dealer is None else dealer

    return TuteState(
        players=[
            TutePlayer(id=i, name=nombre, is_bot=(bots[i] if bots else False),
                       hand=ordenar_mano(manos[i]))
            for i, nombre in enumerate(names)
        ],
        baceta=resto[1:],
        trump_card=trump_card,
        trump_suit=trump_card.suit if trump_card else "o",
        turn=(repartidor + 1) % len(names),
        scores=list(scores) if scores else [0] * len(names),
        events=[{"kind": "deal", "trump": trump_card.id}] if trump_card else [],
    )


def _jugador(state: TuteState, player_id: int) -> TutePlayer:
    if not 0 <= player_id < len(state.players):
        raise TuteError("unknown_player", "ese jugador no está en la mesa")
    return state.players[player_id]


def jugadas_legales(state: TuteState, player_id: int) -> list[Card]:
    """Qué cartas se pueden jugar ahora mismo. Aquí está el juego de verdad."""
    from ..bazas import fuerza

    mano = _jugador(state, player_id).hand
    baza = state.trick
    triunfo = state.trump_suit
    if not baza:
        return list(mano)  # sale el primero: cualquier carta vale

    palo_salida = baza[0][1].suit
    triunfos = [c for c in mano if c.suit == triunfo]

    # Mientras quede baceta: solo es obligatorio asistir al palo de triunfo, sin montar.
    if state.baceta:
        if palo_salida != triunfo:
            return list(mano)
        return triunfos if triunfos else list(mano)

    # Terminada la baceta: asistir, montar y fallar.
    del_palo = [c for c in mano if c.suit == palo_salida]
    if del_palo:
        maxima = max(fuerza(c) for _, c in baza if c.suit == palo_salida)
        que_montan = [c for c in del_palo if fuerza(c) > maxima]
        return que_montan if que_montan else del_palo
    return triunfos if triunfos else list(mano)


def play(state: TuteState, player_id: int, card_id: str) -> None:
    if state.phase != "playing":
        raise TuteError("not_playing", "el juego ya ha terminado")
    if state.turn != player_id:
        raise TuteError("not_your_turn", "ahora no te toca")
    yo = _jugador(state, player_id)
    carta = next((c for c in yo.hand if c.id == card_id), None)
    if carta is None:
        raise TuteError("not_your_card", "esa carta no es tuya")
    if not any(c.id == card_id for c in jugadas_legales(state, player_id)):
        raise TuteError("must_follow", "tienes que asistir, montar o fallar")

    yo.hand = [c for c in yo.hand if c.id != card_id]
    state.trick.append((player_id, carta))
    state.events.append({"kind": "play", "player": player_id, "card": carta.id})
    state.last_winner = None

    if len(state.trick) < len(state.players):
        state.turn = (player_id + 1) % len(state.players)
        return
    _resolver_baza(state)


def cantar(state: TuteState, player_id: int, suit: str) -> None:
    """Cantar un acuse: rey y caballo del mismo palo, después de ganar una baza."""
    if state.phase != "playing":
        raise TuteError("not_playing", "el juego ya ha terminado")
    if state.last_winner != player_id:
        raise TuteError("not_your_trick", "solo se puede cantar después de ganar una baza")
    if player_id in state.cantado_en_esta_baza:
        raise TuteError("already_sung", "solo se puede cantar un acuse por baza")
    mano = _jugador(state, player_id).hand
    tiene_rey = any(c.suit == suit and c.rank == 12 for c in mano)
    tiene_caballo = any(c.suit == suit and c.rank == 11 for c in mano)
    if not (tiene_rey and tiene_caballo):
        raise TuteError("no_acuse", "no tienes rey y caballo de ese palo")

    cuarenta = suit == state.trump_suit
    puntos = ACUSE_TRIUNFO if cuarenta else ACUSE_OTRO
    state.players[player_id].cantados += puntos
    state.cantado_en_esta_baza.append(player_id)
    state.events.append(
        {"kind": "acuse", "player": player_id, "suit": suit, "puntos": puntos, "cuarenta": cuarenta}
    )


def acuses_disponibles(state: TuteState, player_id: int) -> list[str]:
    if state.last_winner != player_id or player_id in state.cantado_en_esta_baza:
        return []
    mano = _jugador(state, player_id).hand
    palos = []
    for suit in PALOS:
        rey = any(c.suit == suit and c.rank == 12 for c in mano)
        caballo = any(c.suit == suit and c.rank == 11 for c in mano)
        if rey and caballo:
            palos.append(suit)
    return palos


def tiene_tute(state: TuteState, player_id: int) -> bool:
    """¿Tiene los cuatro reyes o los cuatro caballos? Eso gana el juego al instante."""
    mano = _jugador(state, player_id).hand
    return any(len({c.suit for c in mano if c.rank == rank}) == 4 for rank in (12, 11))


def cantar_tute(state: TuteState, player_id: int) -> None:
    if not tiene_tute(state, player_id):
        raise TuteError("no_tute", "no tienes los cuatro reyes ni los cuatro caballos")
    state.events.append({"kind": "tute", "player": player_id})
    state.winner = player_id
    state.phase = "match-end"


def _resolver_baza(state: TuteState) -> None:
    ganador = ganador_de_baza(state.trick, state.trump_suit)
    cartas = [c for _, c in state.trick]
    suyo = state.players[ganador]
    suyo.won.extend(cartas)
    state.last_trick = (ganador, list(state.trick))
    state.trick = []
    state.last_winner = ganador
    state.cantado_en_esta_baza = []
    state.events.append({"kind": "trick", "winner": ganador, "tantos": tantos(cartas)})

    # Roba primero el que ha ganado, y luego el resto. La carta que pinta es la última.
    for i in range(len(state.players)):
        _robar(state, (ganador + i) % len(state.players))

    sin_cartas = all(not p.hand for p in state.players)
    sin_baceta = not state.baceta and state.trump_card is None
    if sin_cartas and sin_baceta:
        _terminar_juego(state, ganador)
        return
    state.turn = ganador


def _robar(state: TuteState, player_id: int) -> None:
    jugador = state.players[player_id]
    if state.baceta:
        jugador.hand = ordenar_mano([*jugador.hand, state.baceta[0]])
        state.baceta = state.baceta[1:]
        return
    if state.trump_card is not None:
        jugador.hand = ordenar_mano([*jugador.hand, state.trump_card])
        state.trump_card = None


def _terminar_juego(state: TuteState, ganador_ultima: int) -> None:
    # Los tantos se **acumulan** entre juegos: la partida va a 101 y se llega sumando juegos.
    # Antes se escribían solo los de este juego, así que `scores` nunca pasaba de ~100 y el
    # final de partida de unas líneas más abajo era inalcanzable.
    state.scores = [
        state.scores[p.id]
        + tantos(p.won)
        + p.cantados
        + (DIEZ_ULTIMAS if p.id == ganador_ultima else 0)
        for p in state.players
    ]
    state.events.append(
        {"kind": "game-end", "scores": list(state.scores), "ultima": ganador_ultima}
    )
    campeon = next((i for i, s in enumerate(state.scores) if s >= state.target_tantos), None)
    if campeon is not None:
        state.phase = "match-end"
        state.winner = campeon
        state.events.append({"kind": "match-end", "winner": campeon})
        return
    state.phase = "game-end"
    state.winner = None


def next_game(state: TuteState, rng: random.Random | None = None) -> None:
    """Reparte el juego siguiente, sumando los tantos de este."""
    if state.phase != "game-end":
        raise TuteError("not_finished", "el juego anterior todavía no ha terminado")
    nuevo = new_game(
        names=[p.name for p in state.players],
        bots=[p.is_bot for p in state.players],
        scores=state.scores,
        rng=rng,
    )
    state.players = nuevo.players
    state.baceta = nuevo.baceta
    state.trump_card = nuevo.trump_card
    state.trump_suit = nuevo.trump_suit
    state.turn = nuevo.turn
    state.trick = []
    state.last_trick = None
    state.last_winner = None
    state.cantado_en_esta_baza = []
    state.events = nuevo.events
    state.phase = "playing"
    state.winner = None


def state_for(state: TuteState, seat: int) -> dict:
    """Lo que ve un jugador: su mano y lo que puede hacer; de los demás, solo el recuento."""
    yo = state.players[seat] if 0 <= seat < len(state.players) else None
    return {
        "players": [p.to_dict() for p in state.players],
        "myHand": [c.to_dict() for c in (yo.hand if yo else [])],
        "myWon": [c.to_dict() for c in (yo.won if yo else [])],
        "trumpCard": state.trump_card.to_dict() if state.trump_card else None,
        "trumpSuit": state.trump_suit,
        "bacetaCount": len(state.baceta),
        "turn": state.turn,
        "trick": [{"player": p, "card": c.to_dict()} for p, c in state.trick],
        "lastTrick": (
            {"winner": state.last_trick[0],
             "cards": [{"player": p, "card": c.to_dict()} for p, c in state.last_trick[1]]}
            if state.last_trick
            else None
        ),
        "lastWinner": state.last_winner,
        "jugadasLegales": [c.id for c in jugadas_legales(state, seat)] if yo else [],
        "acuses": acuses_disponibles(state, seat) if yo else [],
        "puedeTute": tiene_tute(state, seat) if yo else False,
        "obligaMontar": not state.baceta,
        "scores": state.scores,
        "targetTantos": state.target_tantos,
        "events": state.events,
        "phase": state.phase,
        "winner": state.winner,
    }
