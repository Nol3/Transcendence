"""El Tute, enchufado a la capa de salas.

El envoltorio fino sobre `engine.py` que pide `apps/salas/juegos.py`. Todo lo demás —códigos,
asientos, reconexión, WebSocket, endpoints— lo pone la sala.
"""
from __future__ import annotations

from typing import Any

from apps.salas.juegos import registrar

from .bots import bot_decision
from .engine import (
    TuteError,
    cantar,
    cantar_tute,
    new_game,
    next_game,
    play,
    state_for,
)


class TuteJuego:
    id = "tute"
    min_jugadores = 2
    max_jugadores = 3  # el de cuatro va por parejas y aún no está
    opciones: dict[str, Any] = {}

    def nuevo_estado(self, nombres: list[str], bots: list[bool], opciones: dict[str, Any]) -> Any:
        return new_game(names=nombres, bots=bots)

    def vista(self, estado: Any, asiento: int | None) -> dict:
        return state_for(estado, asiento if asiento is not None else -1)

    def accion(self, estado: Any, asiento: int, mensaje: dict) -> tuple[str, str] | None:
        action = mensaje.get("action")
        try:
            if action == "play":
                play(estado, asiento, str(mensaje.get("card") or ""))
            elif action == "sing":
                cantar(estado, asiento, str(mensaje.get("suit") or ""))
            elif action == "tute":
                cantar_tute(estado, asiento)
            elif action == "next_game":
                # Repartir el juego siguiente no decide nada: puede pedirlo cualquiera.
                next_game(estado)
            else:
                return ("unknown_action", "Acción desconocida")
        except TuteError as exc:
            return (exc.code, str(exc))
        return None

    def turno_de_bot(self, estado: Any) -> int | None:
        if estado.phase != "playing":
            return None
        # Se mira **solo a los bots**: un bot puede tener algo que hacer fuera de su turno (cantar
        # después de ganar una baza), pero nunca se juega por una persona. Si no se filtra por
        # `is_bot`, el servidor acabaría jugando la mano de un humano.
        for i, jugador in enumerate(estado.players):
            if not jugador.is_bot:
                continue
            if bot_decision(estado, i) is not None:
                return i
        return None

    def jugar_bot(self, estado: Any, asiento: int) -> None:
        decision = bot_decision(estado, asiento)
        if decision is None:
            return
        if decision[0] == "tute":
            cantar_tute(estado, asiento)
        elif decision[0] == "sing":
            cantar(estado, asiento, decision[1])
        else:
            play(estado, asiento, decision[1])

    def en_marcha(self, estado: Any) -> bool:
        return estado.phase == "playing"


registrar(TuteJuego())
