"""La baraja española, compartida por todos los juegos (servidor).

Es el mismo reparto de responsabilidades que en el front (`front/src/app/core/games/baraja.ts`):
aquí vive **lo que es igual en todos los juegos** —palos, valores, construir el mazo, barajar y
repartir— y **no** el orden de fuerza, porque cambia en cada uno:

  - **Culo**: `2 < 3 < 4 < 5 < 6 < 7 < Sota < Caballo < Rey < As`, y por encima de todo el
    **5 de oros** (`apps/culo/engine.py`).
  - **Brisca y tute**: `2 < 4 < 5 < 6 < 7 < Sota < Caballo < Rey < 3 < As` — el **tres** es la
    segunda carta más alta.
  - **Mus**: no hay orden ni palos; solo puntos.

Copiar el orden del Culo al añadir un juego de bazas es el error clásico, y por eso cada juego
trae su tabla en vez de heredarla de aquí.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

# Palos y valores: 1 = As, 2..7, 10 = Sota, 11 = Caballo, 12 = Rey.
SUITS: tuple[str, ...] = ("o", "c", "e", "b")
RANKS: tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7, 10, 11, 12)


@dataclass(frozen=True)
class Card:
    rank: int
    suit: str
    copy: int = 0

    @property
    def id(self) -> str:
        return f"{self.rank}{self.suit}-{self.copy}"

    def to_dict(self) -> dict:
        return {"id": self.id, "rank": self.rank, "suit": self.suit, "copy": self.copy}


def build_deck(decks: int = 1) -> list[Card]:
    return [
        Card(rank=rank, suit=suit, copy=copy)
        for copy in range(decks)
        for suit in SUITS
        for rank in RANKS
    ]


def shuffle(cards: list[Card], rng: random.Random | None = None) -> list[Card]:
    rng = rng or random
    copia = list(cards)
    rng.shuffle(copia)
    return copia


def deal(deck: list[Card], players: int) -> list[list[Card]]:
    """Reparte **todas** las cartas, de una en una y por turnos.

    Con 40 cartas y 6 jugadores no salen iguales, y así es como se juega: el reparto se
    termina y a quien le toque una carta de más, la tiene.
    """
    manos: list[list[Card]] = [[] for _ in range(players)]
    for i, carta in enumerate(deck):
        manos[i % players].append(carta)
    return manos


def deal_some(deck: list[Card], players: int, each: int) -> tuple[list[list[Card]], list[Card]]:
    """Reparte **n** cartas a cada uno y devuelve lo que sobra (el mazo).

    Es lo que necesitan los juegos que no reparten todo de golpe (brisca: 3 cartas y a robar;
    tute: 8 o 10 con baceta).
    """
    manos: list[list[Card]] = [[] for _ in range(players)]
    i = 0
    for _ in range(each):
        for p in range(players):
            if i < len(deck):
                manos[p].append(deck[i])
                i += 1
    return manos, deck[i:]
