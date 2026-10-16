"""El bot de la brisca, en el servidor.

Mismo criterio que el del front: si puede ganar la baza con una carta que no valga tantos, la
gana; si no, suelta la que menos le duela. Guarda ases y treses, y no malgasta un triunfo alto si
la baza no tiene nada que merezca la pena.
"""
from __future__ import annotations

from ..baraja import Card
from ..bazas import FUERZA, PUNTOS, fuerza, puede_ganar
from .engine import BriscaState


def _coste(carta: Card, triunfo: str) -> float:
    """Lo que le duele al bot soltar esta carta."""
    return PUNTOS[carta.rank] + (3 if carta.suit == triunfo else 0) + fuerza(carta) / 10


def _mas_barata(hand: list[Card], triunfo: str) -> Card:
    return min(hand, key=lambda c: (_coste(c, triunfo), FUERZA[c.rank]))


def bot_decision(state: BriscaState, seat: int) -> tuple[str, str] | None:
    """Qué hace el bot: `("play", id)`, `("swap",)` o `None` si no le toca."""
    if state.phase != "playing" or state.turn != seat:
        return None
    yo = state.players[seat]
    if not yo.hand:
        return None

    # Si acaba de ganar una baza y tiene el siete de triunfo, lo cambia: se lleva una carta
    # que vale y deja en la mesa una que no.
    puede_cambiar = (
        state.last_winner == seat
        and state.swap_permitido
        and state.trump_card is not None
        and any(c.rank == 7 and c.suit == state.trump_card.suit for c in yo.hand)
    )
    if puede_cambiar:
        return ("swap", "")

    baza = state.trick
    triunfo = state.trump_suit

    # Si es el último en hablar y ya va ganando, no gasta nada.
    if len(baza) == len(state.players) - 1 and _ganador_parcial(baza, triunfo) == seat:
        return ("play", _mas_barata(yo.hand, triunfo).id)

    # Si puede ganar la baza, la gana con la carta más barata que sirva.
    ganadoras = sorted(
        (c for c in yo.hand if puede_ganar(c, baza, triunfo)), key=lambda c: _coste(c, triunfo)
    )
    if ganadoras:
        return ("play", ganadoras[0].id)
    return ("play", _mas_barata(yo.hand, triunfo).id)


def _ganador_parcial(baza: list[tuple[int, Card]], triunfo: str) -> int:
    from ..bazas import ganador_de_baza

    return ganador_de_baza(baza, triunfo) if baza else -1
