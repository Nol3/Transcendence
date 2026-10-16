"""El Mus, enchufado a la capa de salas.

El envoltorio fino sobre `engine.py` que pide `apps/salas/juegos.py`. Todo lo demás —códigos,
asientos, reconexión, WebSocket, endpoints— lo pone la sala.
"""
from __future__ import annotations

from typing import Any

from apps.salas.juegos import registrar

from .bots import bot_decision
from .engine import (
    JUGADORES,
    MusError,
    cortar_mus,
    decir_mus,
    descartar,
    envidar,
    new_game,
    next_hand,
    no_quiero,
    ordago,
    pasar,
    quiero,
    state_for,
)


class MusJuego:
    id = "mus"
    min_jugadores = JUGADORES
    max_jugadores = JUGADORES
    opciones: dict[str, Any] = {}

    def nuevo_estado(self, nombres: list[str], bots: list[bool], opciones: dict[str, Any]) -> Any:
        return new_game(names=nombres, bots=bots)

    def vista(self, estado: Any, asiento: int | None) -> dict:
        return state_for(estado, asiento if asiento is not None else -1)

    def accion(self, estado: Any, asiento: int, mensaje: dict) -> tuple[str, str] | None:
        action = mensaje.get("action")
        try:
            if action == "mus":
                decir_mus(estado, asiento)
            elif action == "cortar":
                cortar_mus(estado, asiento)
            elif action == "descartar":
                descartar(estado, asiento, list(mensaje.get("cards") or []))
            elif action == "pasar":
                pasar(estado, asiento)
            elif action == "envidar":
                envidar(estado, asiento, int(mensaje.get("cuantas") or 2))
            elif action == "ordago":
                ordago(estado, asiento)
            elif action == "quiero":
                quiero(estado, asiento)
            elif action == "no_quiero":
                no_quiero(estado, asiento)
            elif action == "next_hand":
                next_hand(estado)
            else:
                return ("unknown_action", "Acción desconocida")
        except MusError as exc:
            return (exc.code, str(exc))
        return None

    def turno_de_bot(self, estado: Any) -> int | None:
        if estado.phase in ("game-end", "vaca-end"):
            return None
        # Se mira **solo a los bots**: nunca se juega por una persona.
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
        accion, dato = decision
        if accion == "mus":
            decir_mus(estado, asiento)
        elif accion == "cortar":
            cortar_mus(estado, asiento)
        elif accion == "descartar":
            descartar(estado, asiento, list(dato or []))
        elif accion == "pasar":
            pasar(estado, asiento)
        elif accion == "envidar":
            envidar(estado, asiento, int(dato or 2))
        elif accion == "ordago":
            ordago(estado, asiento)
        elif accion == "quiero":
            quiero(estado, asiento)
        elif accion == "no_quiero":
            no_quiero(estado, asiento)

    def en_marcha(self, estado: Any) -> bool:
        return estado.phase not in ("game-end", "vaca-end")


registrar(MusJuego())
