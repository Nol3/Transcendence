"""Evaluación de manos de póker (la mejor mano de 5 entre 5, 6 o 7 cartas).

La comparación es **lexicográfica**, como manda el póker: primero la categoría y, a
igualdad de categoría, el desempate carta a carta (kickers). No se usa ningún
"score" aditivo: dos manos de la misma categoría se comparan por sus cartas reales.

Referencia de corrección: enumerando las C(52,5) = 2.598.960 manos, el reparto por
categorías coincide exactamente con las frecuencias oficiales del póker
(ver `tests/test_hand_eval.py::test_frecuencias_exhaustivas`).
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from functools import total_ordering
from itertools import combinations

from .cards import Card

HIGH_CARD = 0
ONE_PAIR = 1
TWO_PAIR = 2
THREE_OF_A_KIND = 3
STRAIGHT = 4
FLUSH = 5
FULL_HOUSE = 6
FOUR_OF_A_KIND = 7
STRAIGHT_FLUSH = 8

CATEGORY_NAMES = {
    HIGH_CARD: "Carta alta",
    ONE_PAIR: "Pareja",
    TWO_PAIR: "Doble pareja",
    THREE_OF_A_KIND: "Trío",
    STRAIGHT: "Escalera",
    FLUSH: "Color",
    FULL_HOUSE: "Full house",
    FOUR_OF_A_KIND: "Póker",
    STRAIGHT_FLUSH: "Escalera de color",
}

CATEGORY_SLUGS = {
    HIGH_CARD: "high_card",
    ONE_PAIR: "one_pair",
    TWO_PAIR: "two_pair",
    THREE_OF_A_KIND: "three_of_a_kind",
    STRAIGHT: "straight",
    FLUSH: "flush",
    FULL_HOUSE: "full_house",
    FOUR_OF_A_KIND: "four_of_a_kind",
    STRAIGHT_FLUSH: "straight_flush",
}


@total_ordering
@dataclass(frozen=True, slots=True)
class HandRank:
    """Mano evaluada. Comparable con `<`/`>`/`==` según las reglas del póker."""

    category: int
    tiebreak: tuple[int, ...]  # 5 valores, el mayor primero
    cards: tuple[Card, ...] = ()  # las 5 cartas que forman la mano (informativo)

    @property
    def name(self) -> str:
        return CATEGORY_NAMES[self.category]

    @property
    def slug(self) -> str:
        return CATEGORY_SLUGS[self.category]

    def _key(self) -> tuple[int, tuple[int, ...]]:
        return (self.category, self.tiebreak)

    def __lt__(self, other: HandRank) -> bool:
        if not isinstance(other, HandRank):
            return NotImplemented
        return self._key() < other._key()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, HandRank):
            return NotImplemented
        return self._key() == other._key()

    def __str__(self) -> str:
        return f"{self.name} {'-'.join(str(v) for v in self.tiebreak if v)}".strip()


def _straight_high(unique_ranks_desc: Sequence[int]) -> int | None:
    """Devuelve la carta alta de la escalera, o None. La rueda A-2-3-4-5 vale 5."""
    if len(unique_ranks_desc) != 5:
        return None
    if unique_ranks_desc[0] - unique_ranks_desc[4] == 4:
        return unique_ranks_desc[0]
    if list(unique_ranks_desc) == [14, 5, 4, 3, 2]:  # rueda: el As juega de 1
        return 5
    return None


def evaluate_five(cards: Sequence[Card]) -> HandRank:
    """Evalúa exactamente 5 cartas."""
    if len(cards) != 5:
        raise ValueError(f"se esperaban 5 cartas, hay {len(cards)}")

    ranks = sorted((c.rank for c in cards), reverse=True)
    counts: dict[int, int] = {}
    for r in ranks:
        counts[r] = counts.get(r, 0) + 1

    is_flush = len({c.suit for c in cards}) == 1
    # Grupos ordenados por número de repeticiones y luego por valor.
    groups = sorted(counts.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)
    shape = [n for _, n in groups]
    high = _straight_high(sorted(counts, reverse=True))

    if is_flush and high is not None:
        tb = tuple(high - i for i in range(5))
        return HandRank(STRAIGHT_FLUSH, tb, tuple(cards))

    if shape[0] == 4:
        quad = groups[0][0]
        kicker = groups[1][0]
        return HandRank(FOUR_OF_A_KIND, (quad, kicker, 0, 0, 0), tuple(cards))

    if shape[0] == 3 and shape[1] == 2:
        return HandRank(FULL_HOUSE, (groups[0][0], groups[1][0], 0, 0, 0), tuple(cards))

    if is_flush:
        return HandRank(FLUSH, tuple(ranks), tuple(cards))

    if high is not None:
        tb = tuple(high - i for i in range(5))
        return HandRank(STRAIGHT, tb, tuple(cards))

    if shape[0] == 3:
        trio = groups[0][0]
        kickers = tuple(sorted((r for r, n in groups[1:]), reverse=True))
        return HandRank(
            THREE_OF_A_KIND,
            (trio,) + kickers + (0,) * (2 - len(kickers)),
            tuple(cards),
        )

    if shape[0] == 2 and shape[1] == 2:
        pairs = tuple(sorted((r for r, n in groups if n == 2), reverse=True))
        kicker = next(r for r, n in groups if n == 1)
        return HandRank(TWO_PAIR, (pairs[0], pairs[1], kicker, 0, 0), tuple(cards))

    if shape[0] == 2:
        pair = groups[0][0]
        kickers = tuple(sorted((r for r, n in groups[1:]), reverse=True))
        return HandRank(ONE_PAIR, (pair,) + kickers + (0,) * (3 - len(kickers)), tuple(cards))

    return HandRank(HIGH_CARD, tuple(ranks), tuple(cards))


def evaluate(cards: Sequence[Card]) -> HandRank:
    """Mejor mano de 5 entre las cartas dadas (5, 6 o 7)."""
    cards = list(cards)
    if len(cards) < 5:
        raise ValueError(f"se necesitan al menos 5 cartas, hay {len(cards)}")
    if len(cards) == 5:
        return evaluate_five(cards)
    return max(evaluate_five(combo) for combo in combinations(cards, 5))


def best_hand_from(cards: Sequence[Card]) -> HandRank:
    return evaluate(cards)
