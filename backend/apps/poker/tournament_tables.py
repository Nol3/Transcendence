"""Mesas de póker para los matches de un torneo.

Un match del bracket se juega en una mesa **real** del motor de póker, no en el
juego local: los dos participantes entran por WebSocket a `/ws/poker/table/<id>` y
el resultado lo cierra el servidor cuando la mesa termina (ver
`apps/poker/services.py::_close_tournament_match`).

La mesa se crea **sin repartir** (`start()` se llama al sentarse los dos), para que
nadie pierda la ciega mientras el rival todavía carga la página.
"""
from __future__ import annotations

from .tables import PokerTable, TableSeat, registry

# Ciegas y stack de los matches de torneo (mismo nivel que la cola "low").
TOURNAMENT_BLINDS = {"small_blind": 5, "big_blind": 10, "starting_stack": 1000}


def table_for_match(match_id: int) -> PokerTable | None:
    """Mesa viva (sin terminar) de ese match, si existe."""
    for table in registry.all():
        if (table.context or {}).get("match_id") == match_id and not table.finished:
            return table
    return None


def get_or_create_match_table(match) -> PokerTable:
    """Devuelve la mesa del match, creándola la primera vez.

    Idempotente: los dos jugadores pueden llamar al endpoint y acaban en la misma
    mesa. Se registra con el contexto del match para que el resultado se cierre
    desde el servidor.
    """
    existente = table_for_match(match.id)
    if existente is not None:
        return existente

    if match.player2_id is None:
        raise ValueError("el match no tiene rival (es un pase directo)")

    from .services import report_match_end

    seats = [
        TableSeat(index=0, user_id=match.player1_id, username=match.player1.username,
                  stack=TOURNAMENT_BLINDS["starting_stack"]),
        TableSeat(index=1, user_id=match.player2_id, username=match.player2.username,
                  stack=TOURNAMENT_BLINDS["starting_stack"]),
    ]
    return registry.create(
        seats,
        small_blind=TOURNAMENT_BLINDS["small_blind"],
        big_blind=TOURNAMENT_BLINDS["big_blind"],
        on_match_end=report_match_end,
        context={"tournament_id": match.tournament_id, "match_id": match.id},
    )
