"""Utilidades para construir manos deterministas en los tests.

`build_deck` devuelve las cartas **en el orden exacto en que el motor las roba**:
primero 2 cartas a cada asiento en orden, y luego, por cada calle, una carta
quemada y las comunitarias (3 en el flop, 1 en turn y 1 en river).
"""
from __future__ import annotations

from apps.poker.engine import Card, full_deck, parse_cards


def build_deck(holes: dict[int, str], board: str = "", n_seats: int = 2) -> list[Card]:
    used: list[Card] = []
    per_seat = {i: parse_cards(holes.get(i, "")) for i in range(n_seats)}
    for i in range(n_seats):
        used.extend(per_seat[i])
    board_cards = parse_cards(board)
    used.extend(board_cards)

    filler = iter([c for c in full_deck() if c not in used])

    out: list[Card] = []
    for i in range(n_seats):
        out.extend(per_seat[i])
    if board_cards:
        out.append(next(filler))                      # quemada antes del flop
        out.extend(board_cards[:3])
        if len(board_cards) > 3:
            out.append(next(filler))                  # quemada antes del turn
            out.append(board_cards[3])
        if len(board_cards) > 4:
            out.append(next(filler))                  # quemada antes del river
            out.append(board_cards[4])
    return out
