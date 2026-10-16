"""Lo que comparten los juegos de bazas (brisca y tute), en el servidor.

En los dos se juega una carta, gana la mejor y el que gana se lleva la baza. Aquí está lo común:
**el orden de fuerza** y **lo que vale cada carta**. El orden no es el del Culo ni el de la
baraja: de menor a mayor es `2 < 4 < 5 < 6 < 7 < Sota < Caballo < Rey < 3 < As`. El **tres** es la
segunda carta más alta, no la tercera, que es el error clásico al añadir un juego de bazas.
"""
from __future__ import annotations

from .baraja import Card

#: Fuerza de cada carta. Ojo: el tres va segundo.
FUERZA: dict[int, int] = {2: 1, 4: 2, 5: 3, 6: 4, 7: 5, 10: 6, 11: 7, 12: 8, 3: 9, 1: 10}

#: Tantos que vale cada carta al contar. El resto (7, 6, 5, 4, 2) no valen nada.
PUNTOS: dict[int, int] = {1: 11, 3: 10, 12: 4, 11: 3, 10: 2, 7: 0, 6: 0, 5: 0, 4: 0, 2: 0}

#: De menor a mayor, para el panel de reglas.
ORDEN: tuple[int, ...] = (2, 4, 5, 6, 7, 10, 11, 12, 3, 1)


def fuerza(card: Card) -> int:
    return FUERZA[card.rank]


def puntos(card: Card) -> int:
    return PUNTOS[card.rank]


def tantos(cards: list[Card]) -> int:
    """Cuántos tantos suman unas cartas ganadas (una baza o todas las de la partida)."""
    return sum(puntos(c) for c in cards)


def ganador_de_baza(baza: list[tuple[int, Card]], triunfo: str) -> int:
    """Quién gana la baza.

    Gana la carta más alta **del palo de triunfo**; si no se jugó triunfo, la más alta del palo
    con el que salió el primero. No hay empates posibles: la baraja no repite carta en un palo.
    """
    if not baza:
        return -1
    mejor = baza[0]
    for jugada in baza[1:]:
        suya, mia = jugada[1], mejor[1]
        if suya.suit == triunfo and mia.suit != triunfo:
            gana = True
        elif suya.suit != mia.suit:
            gana = False
        else:
            gana = fuerza(suya) > fuerza(mia)
        if gana:
            mejor = jugada
    return mejor[0]


def puede_ganar(card: Card, baza: list[tuple[int, Card]], triunfo: str) -> bool:
    """¿Puede esta carta ganar la baza que hay ahora mismo en la mesa?"""
    palo_salida = baza[0][1].suit if baza else card.suit
    triunfos = [c for _, c in baza if c.suit == triunfo]
    if card.suit == triunfo:
        return all(fuerza(card) > fuerza(c) for c in triunfos)
    if triunfos:
        return False  # hay triunfo en la mesa y no es tuyo
    if card.suit != palo_salida:
        return False
    return all(fuerza(card) > fuerza(c) for _, c in baza if c.suit == palo_salida)


def ordenar_mano(hand: list[Card]) -> list[Card]:
    """Ordena una mano por palo y, dentro de él, de mayor a menor fuerza."""
    return sorted(hand, key=lambda c: (c.suit, -fuerza(c)))
