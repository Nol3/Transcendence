"""Política de los bots.

No pretenden jugar perfecto: juegan **razonablemente**, con dos ideas que evitan
que sean un saco de fichas:

1. Fuerza de la mano: antes del flop se puntúa la mano inicial (parejas, ases,
   palos conectados); después del flop se usa la categoría real de la mano.
2. Pot odds: se iguala solo si el precio de la apuesta es rentable frente a la
   fuerza estimada, y se sube con manos fuertes.
"""
from __future__ import annotations

import random

from .engine import (
    ALL_IN,
    BET,
    CALL,
    CHECK,
    FLUSH,
    FOLD,
    FOUR_OF_A_KIND,
    FULL_HOUSE,
    ONE_PAIR,
    PREFLOP,
    RAISE,
    STRAIGHT,
    STRAIGHT_FLUSH,
    THREE_OF_A_KIND,
    TWO_PAIR,
    Hand,
    evaluate,
)

# Umbrales de "fuerza" (0..1) para decidir agresividad.
STRONG = 0.72
DECENT = 0.45


def preflop_strength(hole) -> float:
    """Fuerza aproximada de una mano inicial, normalizada a 0..1."""
    a, b = sorted((c.rank for c in hole), reverse=True)
    suited = hole[0].suit == hole[1].suit
    if a == b:                                   # pareja
        return min(1.0, 0.5 + a / 28.0)          # AA ~1.0, 22 ~0.57
    score = (a + b) / 28.0                       # 0..1 por cartas altas
    if a == 14:
        score += 0.15
    if b >= 10:
        score += 0.10
    if suited:
        score += 0.08
    gap = a - b
    if gap == 1:
        score += 0.06
    elif gap > 4:
        score -= 0.08
    return max(0.0, min(1.0, score))


def postflop_strength(hand: Hand, seat_index: int) -> float:
    """Fuerza a partir de la categoría de la mejor mano actual."""
    rank = evaluate(hand.seats[seat_index].hole + hand.board)
    base = {
        ONE_PAIR: 0.45,
        TWO_PAIR: 0.62,
        THREE_OF_A_KIND: 0.75,
        STRAIGHT: 0.85,
        FLUSH: 0.90,
        FULL_HOUSE: 0.95,
        FOUR_OF_A_KIND: 0.99,
        STRAIGHT_FLUSH: 1.0,
    }.get(rank.category, 0.28)                   # carta alta
    # Un top-pair con kicker alto vale algo más.
    if rank.category == ONE_PAIR and rank.tiebreak[0] >= 12:
        base += 0.07
    return min(1.0, base)


def strength(hand: Hand, seat_index: int) -> float:
    if hand.street == PREFLOP:
        return preflop_strength(hand.seats[seat_index].hole)
    return postflop_strength(hand, seat_index)


def decide(hand: Hand, seat_index: int, rng: random.Random | None = None) -> tuple[str, int | None]:
    """Devuelve (acción, amount) para el asiento indicado."""
    rng = rng or random
    options = {o["action"]: o for o in hand.legal_actions(seat_index)}
    if not options:
        return FOLD, None

    seat = hand.seats[seat_index]
    pot = hand.pot_total
    to_call = options.get(CALL, {}).get("amount", 0)
    power = strength(hand, seat_index)
    noise = rng.uniform(-0.06, 0.06)
    power = max(0.0, min(1.0, power + noise))

    can_raise = RAISE in options or BET in options or ALL_IN in options
    pot_odds = (to_call / (pot + to_call)) if (to_call and pot + to_call) else 0.0

    # Mano fuerte: subir (o all-in si el stack es corto).
    if can_raise and power >= STRONG:
        raise_opt = options.get(RAISE) or options.get(BET) or options.get(ALL_IN)
        if raise_opt["action"] == ALL_IN:
            return ALL_IN, None
        target = hand.current_bet + max(hand.last_full_raise, int(pot * 0.6))
        target = max(raise_opt["min"], min(target, raise_opt["max"]))
        if seat.stack <= hand.big_blind * 4:      # stack corto: shove
            return ALL_IN, None
        return raise_opt["action"], target

    # Sin apuesta pendiente: pasar (a veces farolear con mano decente).
    if CHECK in options:
        if power >= DECENT and can_raise and rng.random() < 0.35:
            bet_opt = options.get(BET) or options.get(RAISE)
            if bet_opt:
                target = max(bet_opt["min"], min(int(pot * 0.5) or bet_opt["min"], bet_opt["max"]))
                return bet_opt["action"], target
        return CHECK, None

    # Hay que pagar: comparar fuerza con el precio.
    if to_call >= seat.stack:                     # no le llega para igualar
        return (CALL, None) if power >= DECENT else (FOLD, None)
    if power >= DECENT and power >= pot_odds * 1.15:
        return CALL, None
    if to_call <= hand.big_blind and power >= 0.32:   # barato: ver el flop
        return CALL, None
    return FOLD, None
