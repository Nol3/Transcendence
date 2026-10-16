"""El Mentiroso, enchufado a la capa de salas.

Esto es el envoltorio fino sobre `engine.py` que pide `apps/salas/juegos.py`: arrancar, decir qué
ve cada asiento, aplicar una acción del jugador y mover a los bots. Todo lo demás —códigos,
asientos, reconexión, WebSocket, endpoints— lo pone la sala.
"""
from __future__ import annotations

from typing import Any

from apps.salas.juegos import registrar

from .bots import bot_decision
from .engine import (
    MANOS_POR_DEFECTO,
    MentirosoError,
    desconfiar,
    new_game,
    next_hand,
    play,
    retirar,
    state_for,
)


class MentirosoJuego:
    id = "mentiroso"
    min_jugadores = 3
    max_jugadores = 6
    opciones: dict[str, Any] = {"manos": MANOS_POR_DEFECTO}

    def nuevo_estado(self, nombres: list[str], bots: list[bool], opciones: dict[str, Any]) -> Any:
        try:
            manos = int(opciones.get("manos") or MANOS_POR_DEFECTO)
        except (TypeError, ValueError):
            manos = MANOS_POR_DEFECTO
        return new_game(names=nombres, bots=bots, target_wins=max(1, min(10, manos)))

    def vista(self, estado: Any, asiento: int | None) -> dict:
        return state_for(estado, asiento if asiento is not None else -1)

    def accion(self, estado: Any, asiento: int, mensaje: dict) -> tuple[str, str] | None:
        action = mensaje.get("action")
        try:
            if action == "play":
                play(estado, asiento, mensaje.get("cards") or [], mensaje.get("claimedRank"))
            elif action == "challenge":
                desconfiar(estado, asiento)
            elif action == "retire":
                retirar(estado, asiento, int(mensaje.get("rank")))
            elif action == "next_hand":
                # Repartir la mano siguiente no decide nada del juego, así que puede pedirlo
                # cualquiera de la mesa (no como en el Culo, donde abre ronda el anfitrión).
                next_hand(estado)
            else:
                return ("unknown_action", "Acción desconocida")
        except (MentirosoError, TypeError, ValueError) as exc:
            if isinstance(exc, MentirosoError):
                return (exc.code, str(exc))
            return ("bad_action", "Esa acción no se entiende")
        return None

    def turno_de_bot(self, estado: Any) -> int | None:
        if estado.phase != "playing":
            return None
        jugador = estado.players[estado.turn]
        return estado.turn if jugador.is_bot else None

    def jugar_bot(self, estado: Any, asiento: int) -> None:
        decision = bot_decision(estado, asiento)
        if decision is None:
            return
        if decision[0] == "retire":
            retirar(estado, asiento, decision[1])
        elif decision[0] == "challenge":
            desconfiar(estado, asiento)
        else:
            _, ids, valor = decision
            play(estado, asiento, ids, valor)

    def en_marcha(self, estado: Any) -> bool:
        return estado.phase == "playing"


registrar(MentirosoJuego())
