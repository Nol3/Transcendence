"""Motor de póker: lógica pura, sin Django ni E/S.

Uso:
    from apps.poker.engine import Hand
    h = Hand(stacks=[1000, 1000], button=0, small_blind=5, big_blind=10).start()
    h.act(h.actor, "call")
"""
from .cards import Card, Deck, full_deck, parse_cards
from .game import (
    ALL_IN,
    BET,
    CALL,
    CHECK,
    COMPLETE,
    FLOP,
    FOLD,
    MAX_SEATS,
    MIN_SEATS,
    PREFLOP,
    RAISE,
    RIVER,
    STREET_NAMES,
    TURN,
    Hand,
    IllegalAction,
    Seat,
)
from .hand_eval import (
    CATEGORY_NAMES,
    FLUSH,
    FOUR_OF_A_KIND,
    FULL_HOUSE,
    HIGH_CARD,
    ONE_PAIR,
    STRAIGHT,
    STRAIGHT_FLUSH,
    THREE_OF_A_KIND,
    TWO_PAIR,
    HandRank,
    evaluate,
    evaluate_five,
)

__all__ = [
    "Card", "Deck", "full_deck", "parse_cards",
    "HandRank", "evaluate", "evaluate_five", "CATEGORY_NAMES",
    "HIGH_CARD", "ONE_PAIR", "TWO_PAIR", "THREE_OF_A_KIND", "STRAIGHT",
    "FLUSH", "FULL_HOUSE", "FOUR_OF_A_KIND", "STRAIGHT_FLUSH",
    "Hand", "Seat", "IllegalAction",
    "PREFLOP", "FLOP", "TURN", "RIVER", "COMPLETE", "STREET_NAMES",
    "FOLD", "CHECK", "CALL", "BET", "RAISE", "ALL_IN",
    "MIN_SEATS", "MAX_SEATS",
]
