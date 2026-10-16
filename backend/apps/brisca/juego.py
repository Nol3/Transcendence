"""La Brisca, enchufada a la capa de salas.

El envoltorio fino sobre `engine.py` que pide `apps/salas/juegos.py`. Todo lo demás —códigos,
asientos, reconexión, WebSocket, endpoints— lo pone la sala.
"""
from __future__ import annotations

from typing import Any

from apps.salas.juegos import registrar

from .bots import bot_decision
from .engine import (
    JUEGOS_POR_DEFECTO,
    BriscaError,
    cambiar_triunfo,
    new_game,
    next_game,
    play,
    state_for,
)


class BriscaJuego:
    id = "brisca"
    min_jugadores = 2
    # El de cuatro va por parejas y todavía no está: el motor juega de 2 y de 3.
    max_jugadores = 3
    opciones: dict[str, Any] = {"juegos": JUEGOS_POR_DEFECTO}

    def nuevo_estado(self, nombres: list[str], bots: list[bool], opciones: dict[str, Any]) -> Any:
        try:
            juegos = int(opciones.get("juegos") or JUEGOS_POR_DEFECTO)
        except (TypeError, ValueError):
            juegos = JUEGOS_POR_DEFECTO
        return new_game(names=nombres, bots=bots, target_games=max(1, min(10, juegos)))

    def vista(self, estado: Any, asiento: int | None) -> dict:
        return state_for(estado, asiento if asiento is not None else -1)

    def accion(self, estado: Any, asiento: int, mensaje: dict) -> tuple[str, str] | None:
        action = mensaje.get("action")
        try:
            if action == "play":
                play(estado, asiento, str(mensaje.get("card") or ""))
            elif action == "swap":
                cambiar_triunfo(estado, asiento)
            elif action == "next_game":
                # Repartir el juego siguiente no decide nada: puede pedirlo cualquiera.
                next_game(estado)
            else:
                return ("unknown_action", "Acción desconocida")
        except BriscaError as exc:
            return (exc.code, str(exc))
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
        if decision[0] == "swap":
            cambiar_triunfo(estado, asiento)
        else:
            play(estado, asiento, decision[1])

    def en_marcha(self, estado: Any) -> bool:
        return estado.phase == "playing"


registrar(BriscaJuego())
