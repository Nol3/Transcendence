"""Reglas de la Brisca, en el servidor.

Port fiel del motor que ya está probado en el front (`front/src/app/core/games/brisca/`). En
cuanto la partida es online las reglas **tienen** que vivir aquí: si las decidiera el navegador,
cualquiera podría mirar las cartas del mazo desde la consola.

Lo esencial, tal y como está en las normas:
  - Se reparten 3 cartas a cada uno y se descubre la siguiente, que marca el **triunfo**.
  - Se juega una carta **sin obligación de asistir al palo ni de jugar triunfo**.
  - Gana la más alta del triunfo; si no hay triunfo, la más alta del palo de salida.
  - **El que gana roba primero y sale** en la baza siguiente.
  - La carta que pinta es **la última que se roba**.
  - Al contar, As 11, tres 10, rey 4, caballo 3, sota 2. **Empate a 60 anula el juego.**
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from ..baraja import Card, build_deck, deal_some, shuffle
from ..bazas import ganador_de_baza, ordenar_mano, tantos

MIN_JUGADORES = 2
MAX_JUGADORES = 4
CARTAS_POR_JUGADOR = 3
JUEGOS_POR_DEFECTO = 3
TANTOS_DE_EMPATE = 60


class BriscaError(Exception):
    """Un movimiento imposible, con código corto para que el front lo traduzca."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass
class BriscaPlayer:
    id: int
    name: str
    is_bot: bool = False
    hand: list[Card] = field(default_factory=list)
    #: Las cartas de las bazas que ha ganado.
    won: list[Card] = field(default_factory=list)
    tricks: int = 0
    connected: bool = True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "isBot": self.is_bot,
            "handCount": len(self.hand),
            "tantos": tantos(self.won),
            "tricks": self.tricks,
            "connected": self.connected,
        }


@dataclass
class BriscaState:
    players: list[BriscaPlayer] = field(default_factory=list)
    deck: list[Card] = field(default_factory=list)
    trump_card: Card | None = None
    trump_suit: str = "o"
    turn: int = 0
    trick: list[tuple[int, Card]] = field(default_factory=list)
    last_trick: tuple[int, list[tuple[int, Card]]] | None = None
    last_winner: int | None = None
    swap_permitido: bool = True
    dealer: int = 0
    scores: list[int] = field(default_factory=list)
    games_won: list[int] = field(default_factory=list)
    target_games: int = JUEGOS_POR_DEFECTO
    events: list[dict[str, Any]] = field(default_factory=list)
    phase: str = "playing"  # playing | game-end | match-end
    winner: int | None = None


def new_game(
    names: list[str],
    bots: list[bool] | None = None,
    target_games: int = JUEGOS_POR_DEFECTO,
    dealer: int | None = None,
    games_won: list[int] | None = None,
    rng: random.Random | None = None,
) -> BriscaState:
    if not MIN_JUGADORES <= len(names) <= MAX_JUGADORES:
        raise BriscaError(
            "players", f"la brisca se juega entre {MIN_JUGADORES} y {MAX_JUGADORES} jugadores"
        )
    mazo = shuffle(build_deck(1), rng)
    manos, resto = deal_some(mazo, len(names), CARTAS_POR_JUGADOR)
    # La siguiente carta se descubre: marca el triunfo y es la última que se robará.
    trump_card = resto[0] if resto else None
    repartidor = len(names) - 1 if dealer is None else dealer

    return BriscaState(
        players=[
            BriscaPlayer(id=i, name=nombre, is_bot=(bots[i] if bots else False),
                         hand=ordenar_mano(manos[i]))
            for i, nombre in enumerate(names)
        ],
        deck=resto[1:],
        trump_card=trump_card,
        trump_suit=trump_card.suit if trump_card else "o",
        turn=(repartidor + 1) % len(names),
        dealer=repartidor,
        scores=[0] * len(names),
        games_won=list(games_won) if games_won else [0] * len(names),
        target_games=target_games,
        events=[{"kind": "deal", "trump": trump_card.id}] if trump_card else [],
    )


def _jugador(state: BriscaState, player_id: int) -> BriscaPlayer:
    if not 0 <= player_id < len(state.players):
        raise BriscaError("unknown_player", "ese jugador no está en la mesa")
    return state.players[player_id]


def play(state: BriscaState, player_id: int, card_id: str) -> None:
    """Jugar una carta. No hay obligación de asistir ni de montar: cualquier carta vale."""
    if state.phase != "playing":
        raise BriscaError("not_playing", "el juego ya ha terminado")
    if state.turn != player_id:
        raise BriscaError("not_your_turn", "ahora no te toca")
    yo = _jugador(state, player_id)
    carta = next((c for c in yo.hand if c.id == card_id), None)
    if carta is None:
        raise BriscaError("not_your_card", "esa carta no es tuya")

    yo.hand = [c for c in yo.hand if c.id != card_id]
    state.trick.append((player_id, carta))
    state.events.append({"kind": "play", "player": player_id, "card": carta.id})
    state.last_winner = None

    if len(state.trick) < len(state.players):
        state.turn = (player_id + 1) % len(state.players)
        return
    _resolver_baza(state)


def cambiar_triunfo(state: BriscaState, player_id: int) -> None:
    """Cambiar la carta que pinta por el siete de ese palo.

    Solo quien acaba de ganar una baza, antes de robar y nunca después de la penúltima baza.
    """
    if state.phase != "playing":
        raise BriscaError("not_playing", "el juego ya ha terminado")
    if state.last_winner != player_id:
        raise BriscaError("not_your_trick", "solo puede cambiarlo quien acaba de ganar la baza")
    if not state.swap_permitido:
        raise BriscaError("too_late", "ya no se puede cambiar el triunfo")
    carta = state.trump_card
    if carta is None:
        raise BriscaError("no_trump", "ya no queda carta que pinta")
    yo = _jugador(state, player_id)
    siete = next((c for c in yo.hand if c.rank == 7 and c.suit == carta.suit), None)
    if siete is None:
        raise BriscaError("no_seven", "no tienes el siete de triunfo")

    yo.hand = ordenar_mano([c for c in yo.hand if c.id != siete.id] + [carta])
    state.trump_card = siete
    state.events.append({"kind": "swap", "player": player_id, "card": siete.id})


def _resolver_baza(state: BriscaState) -> None:
    ganador = ganador_de_baza(state.trick, state.trump_suit)
    cartas = [c for _, c in state.trick]
    suyo = state.players[ganador]
    suyo.won.extend(cartas)
    suyo.tricks += 1
    state.last_trick = (ganador, list(state.trick))
    state.trick = []
    state.last_winner = ganador
    state.events.append({"kind": "trick", "winner": ganador, "tantos": tantos(cartas)})

    # Roba primero el que ha ganado la baza, y luego el resto por orden.
    for i in range(len(state.players)):
        _robar(state, (ganador + i) % len(state.players))

    sin_cartas = all(not p.hand for p in state.players)
    if sin_cartas and not state.deck and state.trump_card is None:
        _terminar_juego(state)
        return

    state.turn = ganador  # sale quien ganó
    state.swap_permitido = len(state.deck) > 1


def _robar(state: BriscaState, player_id: int) -> None:
    """Roba del mazo; y cuando el mazo se agota, la carta que pinta es la última."""
    jugador = state.players[player_id]
    if state.deck:
        jugador.hand = ordenar_mano([*jugador.hand, state.deck[0]])
        state.deck = state.deck[1:]
        return
    if state.trump_card is not None:
        jugador.hand = ordenar_mano([*jugador.hand, state.trump_card])
        state.trump_card = None


def _terminar_juego(state: BriscaState) -> None:
    state.scores = [tantos(p.won) for p in state.players]
    # Empate a 60: el juego se anula, no lo gana nadie.
    anulado = (
        len(state.players) == 2
        and state.scores[0] == state.scores[1]
        and state.scores[0] == TANTOS_DE_EMPATE
    )
    ganador: int | None = None
    if not anulado:
        maximo = max(state.scores)
        if state.scores.count(maximo) == 1:
            ganador = state.scores.index(maximo)
    if ganador is not None:
        state.games_won[ganador] += 1
    state.events.append({"kind": "game-end", "scores": list(state.scores), "anulado": anulado})
    state.winner = ganador

    campeon = next((i for i, g in enumerate(state.games_won) if g >= state.target_games), None)
    if campeon is not None:
        state.phase = "match-end"
        state.winner = campeon
        state.events.append({"kind": "match-end", "winner": campeon})
        return
    state.phase = "game-end"


def next_game(state: BriscaState, rng: random.Random | None = None) -> None:
    """Reparte el juego siguiente. Solo tiene sentido cuando el anterior ha terminado."""
    if state.phase != "game-end":
        raise BriscaError("not_finished", "el juego anterior todavía no ha terminado")
    nuevo = new_game(
        names=[p.name for p in state.players],
        bots=[p.is_bot for p in state.players],
        target_games=state.target_games,
        dealer=(state.dealer + 1) % len(state.players),
        games_won=state.games_won,
        rng=rng,
    )
    state.players = nuevo.players
    state.deck = nuevo.deck
    state.trump_card = nuevo.trump_card
    state.trump_suit = nuevo.trump_suit
    state.turn = nuevo.turn
    state.trick = []
    state.last_trick = None
    state.last_winner = None
    state.swap_permitido = True
    state.dealer = nuevo.dealer
    state.scores = nuevo.scores
    state.events = nuevo.events
    state.phase = "playing"
    state.winner = None


def puede_cambiar_triunfo(state: BriscaState, player_id: int) -> bool:
    if not state.swap_permitido or state.last_winner != player_id or state.trump_card is None:
        return False
    return any(
        c.rank == 7 and c.suit == state.trump_card.suit for c in state.players[player_id].hand
    )


def state_for(state: BriscaState, seat: int) -> dict:
    """Lo que ve un jugador: su mano y sus bazas; de los demás, solo el recuento."""
    yo = state.players[seat] if 0 <= seat < len(state.players) else None
    return {
        "players": [p.to_dict() for p in state.players],
        "myHand": [c.to_dict() for c in (yo.hand if yo else [])],
        "myWon": [c.to_dict() for c in (yo.won if yo else [])],
        "trumpCard": state.trump_card.to_dict() if state.trump_card else None,
        "trumpSuit": state.trump_suit,
        "deckCount": len(state.deck),
        "turn": state.turn,
        "trick": [{"player": p, "card": c.to_dict()} for p, c in state.trick],
        "lastTrick": (
            {"winner": state.last_trick[0],
             "cards": [{"player": p, "card": c.to_dict()} for p, c in state.last_trick[1]]}
            if state.last_trick
            else None
        ),
        "lastWinner": state.last_winner,
        "swapPermitido": state.swap_permitido,
        "scores": state.scores,
        "gamesWon": state.games_won,
        "targetGames": state.target_games,
        "events": state.events,
        "phase": state.phase,
        "winner": state.winner,
    }
