"""El bot del Tute, en el servidor.

Mismo criterio que el del front: canta lo que puede cantar (el tute gana el juego y un acuse son
tantos gratis) y juega respetando las obligaciones, eligiendo entre las cartas legales que le dice
el motor: gana la baza con la más barata que sirva o suelta la que menos le duela.
"""
from __future__ import annotations

from ..baraja import Card
from ..bazas import PUNTOS, fuerza
from .engine import TuteState, acuses_disponibles, jugadas_legales, tiene_tute


def _coste(carta: Card, triunfo: str) -> float:
    return PUNTOS[carta.rank] + (3 if carta.suit == triunfo else 0) + fuerza(carta) / 10


def _mas_barata(legales: list[Card], triunfo: str) -> Card:
    return min(legales, key=lambda c: (_coste(c, triunfo), fuerza(c)))


def _ganaria(baza: list[tuple[int, Card]], carta: Card, triunfo: str) -> bool:
    con_carta = [*baza, (-1, carta)]
    palo_salida = con_carta[0][1].suit
    mejor = con_carta[0]
    for jugada in con_carta[1:]:
        suya, mia = jugada[1], mejor[1]
        if suya.suit == triunfo and mia.suit != triunfo:
            gana = True
        elif suya.suit != mia.suit:
            gana = False
        else:
            gana = fuerza(suya) > fuerza(mia)
        if gana:
            mejor = jugada
    del palo_salida
    return mejor[0] == -1


def bot_decision(state: TuteState, seat: int) -> tuple[str, str] | None:
    """Qué hace el bot: `("tute",)`, `("sing", palo)`, `("play", id)` o `None`."""
    if state.phase != "playing":
        return None

    if tiene_tute(state, seat):
        return ("tute", "")

    acuses = acuses_disponibles(state, seat)
    if acuses:
        cuarenta = state.trump_suit if state.trump_suit in acuses else acuses[0]
        return ("sing", cuarenta)

    if state.turn != seat:
        return None
    legales = jugadas_legales(state, seat)
    if not legales:
        return None

    triunfo = state.trump_suit
    ganadoras = sorted(
        (c for c in legales if _ganaria(state.trick, c, triunfo)),
        key=lambda c: _coste(c, triunfo),
    )
    if ganadoras:
        return ("play", ganadoras[0].id)
    return ("play", _mas_barata(legales, triunfo).id)
