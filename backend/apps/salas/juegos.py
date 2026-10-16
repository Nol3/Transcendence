"""El contrato que cumple cada juego para poder jugarse en una sala.

Una sala no sabe de cartas: sabe de códigos, de asientos, de quién es el anfitrión y de quién
está conectado. Lo que sí sabe es que hay **un juego** detrás, y para eso le pide seis cosas.
Todo lo que no esté aquí es del juego, no de la sala.

Así, añadir un juego online es escribir este objeto (un envoltorio fino sobre su motor, que ya
está probado) y registrarlo. No hay que copiar la sala, ni el WebSocket, ni los endpoints.
"""
from __future__ import annotations

from typing import Any, Protocol


class Juego(Protocol):
    """Lo que un juego tiene que saber hacer para vivir en una sala."""

    #: Identificador corto y estable (`culo`, `mentiroso`…). Da la ruta y el grupo del WS.
    id: str
    #: Cuántos hacen falta para empezar y cuántos caben.
    min_jugadores: int
    max_jugadores: int
    #: Ajustes que puede elegir quien crea la sala (barajas, manos…), con sus valores por
    #: defecto. Sirven para no tener que tocar la sala al añadir un juego con más opciones.
    opciones: dict[str, Any]

    def nuevo_estado(self, nombres: list[str], bots: list[bool], opciones: dict[str, Any]) -> Any:
        """Arranca la partida. `nombres` va en orden de asiento."""

    def vista(self, estado: Any, asiento: int | None) -> dict:
        """Lo que ve ese asiento. `asiento=None` es un espectador (o el lobby)."""

    def accion(self, estado: Any, asiento: int, mensaje: dict) -> tuple[str, str] | None:
        """Aplica una acción del jugador.

        Devuelve `None` si fue bien, o `(código, texto)` si no: el código es lo que traduce el
        front y el texto el respaldo en español. **El servidor valida aquí**, no en el cliente.
        """

    def turno_de_bot(self, estado: Any) -> int | None:
        """A quién le toca, si le toca a un bot. `None` si le toca a una persona."""

    def jugar_bot(self, estado: Any, asiento: int) -> None:
        """Que juegue el bot de ese asiento."""

    def en_marcha(self, estado: Any) -> bool:
        """Si la partida sigue viva (para saber cuándo parar el avance automático)."""


#: Los juegos que se pueden jugar en una sala, por id.
JUEGOS: dict[str, Juego] = {}


def registrar(juego: Juego) -> Juego:
    """Apunta un juego para que las salas puedan usarlo."""
    JUEGOS[juego.id] = juego
    return juego


def get(juego_id: str) -> Juego:
    """El juego con ese id. Falla claro si no existe, en vez de devolver `None`."""
    juego = JUEGOS.get(juego_id)
    if juego is None:
        raise KeyError(f"no hay ningún juego registrado con el id «{juego_id}»")
    return juego
