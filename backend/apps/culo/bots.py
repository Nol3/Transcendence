"""Cómo juegan los bots del Culo, en el servidor.

Port del bot que ya jugaba en el front. No pretenden ser brillantes, pero sí jugar como
juega una persona: no regalan las cartas altas, aprovechan para descartarse cuando están
cerca del final y, al abrir, eligen el tamaño de la jugada pensando en lo que dejan
hacer a los demás.
"""
from __future__ import annotations

import random

from .engine import Card, GameState, legal_combos, strength


def bot_decision(state: GameState, player_id: int,
                 rng: random.Random | None = None) -> list[Card] | None:
    """Cartas que juega el bot, o `None` si pasa."""
    rng = rng or random
    jugadas = legal_combos(state, player_id)
    if not jugadas:
        return None

    mano = state.players[player_id].hand

    # 1) Si puede quedarse sin cartas de una vez, lo hace: es el objetivo del juego.
    for jugada in jugadas:
        if len(jugada) == len(mano):
            return jugada

    # 2) Si le quedan pocas cartas, juega: está a punto de ser Presidente.
    if len(mano) <= 2:
        return _cheapest(jugadas)

    mejor = _cheapest(jugadas)
    valor = strength(mejor[0])

    # 3) Guardarse las cartas altas es legítimo: si la única salida es jugar algo muy
    #    alto y todavía tiene mano de sobra, a veces pasa.
    if state.table is not None and valor >= 9 and len(mano) > 4 and rng.random() < 0.45:
        return None

    # 4) Abriendo: cuantas más cartas juegue de golpe, menos respuestas deja.
    if state.table is None:
        grande = max(jugadas, key=lambda j: (len(j), -strength(j[0])))
        if len(grande) >= 3:
            return grande

    return mejor


def _cheapest(jugadas: list[list[Card]]) -> list[Card]:
    """La jugada que menos fuerza gasta, para no malgastar cartas altas."""
    return min(jugadas, key=lambda j: (strength(j[0]), len(j)))
