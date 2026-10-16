"""Cartas y baraja.

Baraja con `secrets.SystemRandom`: el servidor es el único que baraja, así que la
secuencia **tiene** que ser impredecible (con `random` sembrado, un jugador podría
deducir las cartas). El RNG es inyectable para poder escribir tests deterministas.
"""
from __future__ import annotations

import secrets
from collections.abc import Iterator, Sequence
from dataclasses import dataclass

RANKS = "23456789TJQKA"
SUITS = "cdhs"
RANK_VALUE = {r: i + 2 for i, r in enumerate(RANKS)}  # '2'->2 ... 'A'->14
VALUE_RANK = {v: r for r, v in RANK_VALUE.items()}
SUIT_NAMES = {"c": "tréboles", "d": "diamantes", "h": "corazones", "s": "picas"}


@dataclass(frozen=True, slots=True)
class Card:
    rank: int  # 2..14 (14 = As)
    suit: int  # 0=tréboles 1=diamantes 2=corazones 3=picas

    def __str__(self) -> str:  # "As", "Td", "9c"
        return VALUE_RANK[self.rank] + SUITS[self.suit]

    def __repr__(self) -> str:
        return f"Card('{self}')"

    @property
    def is_red(self) -> bool:
        return self.suit in (1, 2)

    @classmethod
    def parse(cls, text: str) -> Card:
        """'As' / 'A s' / 'as' -> Card(14, 3). Acepta mayúsculas y minúsculas."""
        t = text.strip()
        if len(t) != 2:
            raise ValueError(f"carta inválida: {text!r}")
        rank_ch, suit_ch = t[0].upper(), t[1].lower()
        if rank_ch not in RANK_VALUE or suit_ch not in SUITS:
            raise ValueError(f"carta inválida: {text!r}")
        return cls(RANK_VALUE[rank_ch], SUITS.index(suit_ch))


def parse_cards(text: str) -> list[Card]:
    """'As Kd 9c' -> [Card, Card, Card]."""
    return [Card.parse(tok) for tok in text.replace(",", " ").split()]


def full_deck() -> list[Card]:
    return [Card(rank, suit) for suit in range(4) for rank in range(2, 15)]


class Deck:
    """Mazo de 52 cartas. `shuffle()` usa un RNG criptográfico por defecto."""

    def __init__(
        self,
        cards: Sequence[Card] | None = None,
        rng: secrets.SystemRandom | None = None,
    ):
        self._rng = rng or secrets.SystemRandom()
        self.cards: list[Card] = list(cards) if cards is not None else full_deck()
        self._index = 0

    def shuffle(self) -> None:
        # Fisher-Yates con RNG impredecible.
        for i in range(len(self.cards) - 1, 0, -1):
            j = self._rng.randrange(i + 1)
            self.cards[i], self.cards[j] = self.cards[j], self.cards[i]
        self._index = 0

    def draw(self, n: int = 1) -> list[Card]:
        out = self.cards[self._index:self._index + n]
        if len(out) < n:
            raise ValueError("mazo agotado")
        self._index += n
        return out

    def burn(self, n: int = 1) -> list[Card]:
        """Quema cartas (como en el juego real, para que el reparto sea creíble)."""
        return self.draw(n)

    @property
    def remaining(self) -> int:
        return len(self.cards) - self._index

    def __iter__(self) -> Iterator[Card]:
        return iter(self.cards)
