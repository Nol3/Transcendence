"""El bot del Mentiroso, en el servidor.

Es el mismo criterio que el del front (`mentiroso-bots.ts`): echa lo que dice que echa cuando lo
tiene, cuando no miente con la carta que menos le sirve, retira los cuatro iguales y desconfía
cuando las cuentas no le salen — si entre lo puesto y lo que él tiene se juntan tres del valor que
se está diciendo, al de antes no le quedan.

No necesita saber nada que no esté en su vista, así que sirve igual para llenar una mesa a medias.
"""
from __future__ import annotations

import random

from .engine import MentirosoState

#: A partir de cuántas cartas del valor anunciado (entre la mesa y su mano) el bot sospecha.
SOSPECHA = 3
#: Y de vez en cuando desconfía aunque no le salgan las cuentas: un farol se huele.
PROBABILIDAD_FAROL = 0.12


def bot_decision(
    state: MentirosoState, seat: int, aleatorio: random.Random | None = None
) -> tuple | None:
    """Qué hace el bot en su turno.

    Devuelve `("retire", valor)`, `("challenge",)`, `("play", [ids], valor)` o `None` si no le
    toca. En ese orden de prioridad.
    """
    if state.phase != "playing" or state.turn != seat:
        return None
    yo = state.players[seat]
    if not yo.hand:
        return None
    rng = aleatorio or random

    # Los cuatro iguales se retiran sin pensarlo: son cartas que ya no valen para nada.
    cuenta: dict[int, int] = {}
    for carta in yo.hand:
        cuenta[carta.rank] = cuenta.get(carta.rank, 0) + 1
    cuatro = next((r for r, n in cuenta.items() if n == 4), None)
    if cuatro is not None:
        return ("retire", cuatro)

    # ¿Desconfío?
    ultima = state.last_play
    if ultima is not None and ultima.player != seat:
        en_la_mesa = sum(1 for c in state.pile if c.rank == ultima.claimed_rank)
        mias = sum(1 for c in yo.hand if c.rank == ultima.claimed_rank)
        if en_la_mesa + mias >= SOSPECHA or rng.random() < PROBABILIDAD_FAROL:
            return ("challenge",)

    # El valor que toca: el que hay en la mesa, o el que más le convenga si abre.
    valor = state.claimed_rank
    if valor is None:
        valor = max(cuenta.items(), key=lambda kv: (kv[1], -kv[0]))[0]

    # Si tiene de verdad, las echa todas (se quita cartas de encima).
    reales = [c for c in yo.hand if c.rank == valor]
    if reales:
        return ("play", [c.id for c in reales], valor)

    # Y si no, miente con la que menos le sirve: la menos repetida, para no romper un trío.
    candidata = min(yo.hand, key=lambda c: (cuenta.get(c.rank, 0), c.rank))
    return ("play", [candidata.id], valor)
