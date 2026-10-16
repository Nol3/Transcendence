"""Reglas del Mentiroso, en el servidor.

Es un port fiel del motor que ya está probado en el front
(`front/src/app/core/games/mentiroso/mentiroso-engine.ts`). En cuanto la partida es online las
reglas **tienen** que vivir aquí: si las decidiera el navegador, cualquiera podría mirar el
montón desde la consola. Y en este juego eso es especialmente grave, porque **el farol es el
juego**: el servidor es el único que sabe qué hay debajo de cada carta.

Lo esencial, tal y como está escrito en las normas:

  - Se reparte **toda** la baraja.
  - Por turnos se echan una o varias cartas **boca abajo** diciendo qué son: se puede mentir
    en el **valor**, nunca en la **cantidad** (la cantidad que se anuncia es la que se pone).
  - El valor lo fija quien abre la ronda y los demás lo siguen.
  - **Cualquiera** —no solo el siguiente— puede gritar «¡mentiroso!». Si el que puso decía la
    verdad se lleva el montón quien desconfió; si mentía, se lo lleva quien puso. Y quien se
    lleva el montón abre la ronda siguiente.
  - A quien se ha quedado sin cartas **no se le puede desconfiar**: la jugada que vacía una
    mano es gratis.
  - Gana la mano quien se queda sin cartas, y la partida va a varias manos.

Las funciones que **deciden** son puras; las que **avanzan** la partida modifican el estado que
se les pasa, que es uno por sala y solo lo toca su consumidor.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from ..baraja import Card, build_deck, deal, shuffle

MIN_JUGADORES = 3
MAX_JUGADORES = 6
MANOS_POR_DEFECTO = 3


class MentirosoError(Exception):
    """Un movimiento imposible, con código corto para que el front lo traduzca."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass
class MentirosoPlayer:
    id: int
    name: str
    is_bot: bool = False
    hand: list[Card] = field(default_factory=list)
    #: Los cuatro iguales que ha retirado (ya no juegan).
    retired: list[Card] = field(default_factory=list)
    wins: int = 0
    connected: bool = True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "isBot": self.is_bot,
            "handCount": len(self.hand),
            "wins": self.wins,
            "connected": self.connected,
        }


@dataclass
class MentirosoPlay:
    """Lo último que se puso boca abajo, que es lo que se puede desconfiar."""

    player: int
    cards: list[Card]
    claimed_rank: int


@dataclass
class MentirosoState:
    players: list[MentirosoPlayer] = field(default_factory=list)
    pile: list[Card] = field(default_factory=list)
    #: El valor que hay que seguir; `None` si quien abre aún no lo ha dicho.
    claimed_rank: int | None = None
    turn: int = 0
    last_play: MentirosoPlay | None = None
    hand: int = 1
    target_wins: int = MANOS_POR_DEFECTO
    events: list[dict[str, Any]] = field(default_factory=list)
    phase: str = "playing"  # playing | hand-end | match-end
    winner: int | None = None


def new_game(
    names: list[str],
    bots: list[bool] | None = None,
    target_wins: int = MANOS_POR_DEFECTO,
    rng: random.Random | None = None,
) -> MentirosoState:
    if not MIN_JUGADORES <= len(names) <= MAX_JUGADORES:
        raise MentirosoError(
            "players", f"el mentiroso se juega entre {MIN_JUGADORES} y {MAX_JUGADORES} jugadores"
        )
    manos = deal(shuffle(build_deck(1), rng), len(names))
    return MentirosoState(
        players=[
            MentirosoPlayer(
                id=i, name=nombre, is_bot=(bots[i] if bots else False), hand=manos[i]
            )
            for i, nombre in enumerate(names)
        ],
        target_wins=target_wins,
    )


def _jugador(state: MentirosoState, player_id: int) -> MentirosoPlayer:
    if not 0 <= player_id < len(state.players):
        raise MentirosoError("unknown_player", "ese jugador no está en la mesa")
    return state.players[player_id]


def play(
    state: MentirosoState,
    player_id: int,
    card_ids: list[str],
    claimed_rank: int | None = None,
) -> None:
    """Poner cartas boca abajo diciendo qué son.

    `card_ids` son cartas **de tu mano**; `claimed_rank` es lo que dices que son. Si abres la
    ronda lo eliges tú; si no, tiene que ser el mismo que hay en la mesa (mentir sobre el valor
    es el juego; cambiar el valor que se sigue, no).
    """
    if state.phase != "playing":
        raise MentirosoError("not_playing", "la mano ya ha terminado")
    if state.turn != player_id:
        raise MentirosoError("not_your_turn", "ahora no te toca")
    if not card_ids:
        raise MentirosoError("no_cards", "hay que poner al menos una carta")

    yo = _jugador(state, player_id)
    cartas: list[Card] = []
    for cid in card_ids:
        carta = next((c for c in yo.hand if c.id == cid), None)
        if carta is None:
            raise MentirosoError("not_your_card", "esa carta no es tuya")
        cartas.append(carta)

    valor = state.claimed_rank if state.claimed_rank is not None else claimed_rank
    if valor is None:
        raise MentirosoError("no_rank", "hay que decir qué cartas son")
    cambia_el_valor = (
        state.claimed_rank is not None
        and claimed_rank is not None
        and claimed_rank != state.claimed_rank
    )
    if cambia_el_valor:
        raise MentirosoError("rank_changed", "hay que seguir el valor que hay en la mesa")

    ids = {c.id for c in cartas}
    yo.hand = [c for c in yo.hand if c.id not in ids]
    state.pile.extend(cartas)
    state.claimed_rank = valor
    state.last_play = MentirosoPlay(player=player_id, cards=cartas, claimed_rank=valor)
    state.events.append(
        {"kind": "play", "player": player_id, "count": len(cartas), "claimedRank": valor}
    )

    if not yo.hand:
        _terminar_mano(state, player_id)
        return
    state.turn = (player_id + 1) % len(state.players)


def desconfiar(state: MentirosoState, challenger_id: int) -> None:
    """Gritar «¡mentiroso!». Puede hacerlo cualquiera, no solo el siguiente."""
    if state.phase != "playing":
        raise MentirosoError("not_playing", "la mano ya ha terminado")
    ultima = state.last_play
    if ultima is None:
        raise MentirosoError("nothing_to_challenge", "todavía no hay nada que desconfiar")
    acusador = _jugador(state, challenger_id)
    if acusador.id == ultima.player:
        raise MentirosoError("self_challenge", "no te puedes desconfiar a ti mismo")
    if not _jugador(state, ultima.player).hand:
        raise MentirosoError("player_out", "a quien se ha quedado sin cartas no se le desconfía")

    mentira = any(c.rank != ultima.claimed_rank for c in ultima.cards)
    se_lleva = ultima.player if mentira else challenger_id

    cuantas = len(state.pile)
    state.players[se_lleva].hand.extend(state.pile)
    state.pile = []
    state.claimed_rank = None
    state.last_play = None
    state.turn = se_lleva
    state.events.append({"kind": "challenge", "player": challenger_id, "against": ultima.player})
    state.events.append(
        {"kind": "take", "player": se_lleva, "count": cuantas, "mentira": mentira}
    )


def retirar(state: MentirosoState, player_id: int, rank: int) -> None:
    """Enseñar los cuatro iguales y sacarlos del juego (variante española)."""
    if state.phase != "playing":
        raise MentirosoError("not_playing", "la mano ya ha terminado")
    yo = _jugador(state, player_id)
    cuatro = [c for c in yo.hand if c.rank == rank]
    if len(cuatro) < 4:
        raise MentirosoError("not_four", "hacen falta las cuatro cartas del mismo valor")

    yo.hand = [c for c in yo.hand if c.rank != rank]
    yo.retired.extend(cuatro)
    state.events.append({"kind": "retire", "player": player_id, "rank": rank})
    if not yo.hand:
        _terminar_mano(state, player_id)


def _terminar_mano(state: MentirosoState, ganador: int) -> None:
    state.players[ganador].wins += 1
    state.phase = "match-end" if state.players[ganador].wins >= state.target_wins else "hand-end"
    state.winner = ganador
    state.events.append({"kind": "out", "player": ganador, "wins": state.players[ganador].wins})


def next_hand(state: MentirosoState, rng: random.Random | None = None) -> None:
    """Reparte la mano siguiente. Solo tiene sentido cuando la anterior ha terminado."""
    if state.phase != "hand-end":
        raise MentirosoError("not_finished", "la mano anterior todavía no ha terminado")

    manos = deal(shuffle(build_deck(1), rng), len(state.players))
    for i, jugador in enumerate(state.players):
        jugador.hand = manos[i]
        jugador.retired = []
    state.pile = []
    state.claimed_rank = None
    state.turn = state.winner if state.winner is not None else 0
    state.last_play = None
    state.hand += 1
    state.events = []
    state.phase = "playing"
    state.winner = None


def state_for(state: MentirosoState, seat: int) -> dict:
    """Lo que ve un jugador: **su** mano entera y, de los demás, solo cuántas cartas les quedan.

    El montón no se revela nunca (eso es el juego); lo que sí se ve es el valor que se sigue.
    """
    mia = state.players[seat].hand if 0 <= seat < len(state.players) else []
    return {
        "players": [p.to_dict() for p in state.players],
        "myHand": [c.to_dict() for c in mia],
        "claimedRank": state.claimed_rank,
        "pileCount": len(state.pile),
        "turn": state.turn,
        "hand": state.hand,
        "targetWins": state.target_wins,
        "events": state.events,
        "phase": state.phase,
        "winner": state.winner,
    }
