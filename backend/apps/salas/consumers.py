"""WebSocket de una sala: `/ws/salas/<juego>/<código>?token=...`

El servidor es el que decide. Todo lo que llega del cliente son **peticiones** (`play`, `start`,
`add_bot`…): se las pasa al juego, que valida contra el estado real, y cada conexión recibe **su**
vista, así que las cartas de los demás no salen de aquí.

Esto era del Culo y ahora vale para cualquier juego: lo único que cambia de uno a otro es el
objeto que se registra en `juegos.py`. Los bots juegan solos, con una pausa entre turnos para que
se pueda seguir la partida, y si a alguien se le cae la conexión se le guarda el asiento para que
pueda volver a entrar.
"""
from __future__ import annotations

import asyncio
import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from apps.users.ws_auth import authenticate_ws

from .rooms import Sala, SalaError, registry

# Pausa entre turnos de bot: se juega solo, pero a ritmo de persona.
BOT_DELAY = 0.9

# Códigos de cierre propios, para que el cliente sepa qué ha pasado.
CLOSE_SIN_SESION = 4401
CLOSE_SALA_NO_EXISTE = 4404
CLOSE_SALA_LLENA = 4409


def _group(sala: Sala) -> str:
    return f"sala_{sala.juego_id}_{sala.code}"


async def _broadcast(sala: Sala) -> None:
    """Envía a cada jugador su propia vista de la sala (y de la partida)."""
    from channels.layers import get_channel_layer

    layer = get_channel_layer()
    if layer is None:
        return
    for i, jugador in enumerate(sala.players):
        if jugador.is_bot or not jugador.channel:
            continue
        await layer.send(
            jugador.channel,
            {
                "type": "room.state",
                "payload": sala.to_dict(viewer_id=jugador.user_id),
                "seat": i,
            },
        )


def start_drive(sala: Sala) -> None:
    """Arranca (si no está ya) el avance automático de la partida.

    Se guarda la tarea en la propia sala para poder pararla cuando no queda nadie: si no, quedaría
    un bucle de bots corriendo por una sala que ya no existe.
    """
    tarea = getattr(sala, "_drive_task", None)
    if tarea is not None and not tarea.done():
        return
    sala._drive_task = asyncio.create_task(_drive(sala))  # type: ignore[attr-defined]


async def _drive(sala: Sala) -> None:
    """Hace avanzar la partida sola: turnos de bot hasta que le toca a una persona.

    Si le toca a alguien que está desconectado, **se le espera**: en estos juegos no se puede
    jugar por otro sin romper las reglas (en el Mentiroso, decidir si desconfías es tuyo y de
    nadie más), así que la mesa aguanta a que vuelva. Al recargar la página se vuelve al mismo
    asiento.
    """
    if getattr(sala, "_driving", False):
        return
    sala._driving = True  # type: ignore[attr-defined]
    try:
        while sala.status == "playing" and sala.state is not None:
            seat = sala.juego.turno_de_bot(sala.state)
            if seat is None:
                return  # le toca a una persona: aquí se para
            await asyncio.sleep(BOT_DELAY)
            if sala.status != "playing" or sala.state is None:
                return
            if sala.juego.turno_de_bot(sala.state) != seat:
                return  # ha cambiado el turno mientras el bot pensaba
            sala.juego.jugar_bot(sala.state, seat)
            await _broadcast(sala)
    except asyncio.CancelledError:
        # La sala se ha quedado sin nadie: se para sin ruido.
        pass
    finally:
        sala._driving = False  # type: ignore[attr-defined]


class SalaConsumer(AsyncWebsocketConsumer):
    """Una conexión = un asiento de una sala."""

    sala: Sala | None = None
    user_id: int | None = None
    seat: int | None = None

    async def connect(self):
        self.code = self.scope["url_route"]["kwargs"]["code"].upper()
        # La validación del JWT consulta la base de datos, y eso no se puede hacer desde código
        # async: se manda a un hilo (mismo patrón que la mesa de póker).
        credenciales = await sync_to_async(authenticate_ws, thread_sensitive=True)(self.scope)
        if credenciales is None:
            await self.close(code=CLOSE_SIN_SESION)
            return
        self.user_id, self.username = credenciales

        sala = registry.get(self.code)
        if sala is None:
            await self.close(code=CLOSE_SALA_NO_EXISTE)
            return
        try:
            sala.join(self.user_id, self.username, self.channel_name)
        except SalaError as exc:
            await self.accept()
            await self.send(
                text_data=json.dumps({"type": "error", "code": exc.code, "message": str(exc)})
            )
            await self.close(code=CLOSE_SALA_LLENA)
            return

        self.sala = sala
        self.seat = sala.seat_of(self.user_id)
        await self.channel_layer.group_add(_group(sala), self.channel_name)
        await self.accept()
        await _broadcast(sala)
        # Si la partida ya estaba en marcha, puede que le toque a un bot.
        start_drive(sala)

    async def disconnect(self, close_code):
        sala = self.sala
        if sala is not None and self.user_id is not None:
            # Se le pasa el canal para no dar por ido a quien ya ha vuelto con otra conexión
            # (recarga de página, móvil que vuelve del segundo plano).
            if sala.disconnect(self.user_id, self.channel_name):
                await _broadcast(sala)
            # Si ya no queda nadie, se para el avance automático de la partida.
            if sala.empty:
                tarea = getattr(sala, "_drive_task", None)
                if tarea is not None and not tarea.done():
                    tarea.cancel()
        await self.channel_layer.group_discard(_group(sala), self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if self.sala is None or self.user_id is None or self.seat is None:
            return
        try:
            mensaje = json.loads(text_data or "{}")
        except json.JSONDecodeError:
            return
        await self._handle(mensaje.get("action"), mensaje)

    # ── Acciones ─────────────────────────────────────────────────────────────

    async def _handle(self, action, mensaje: dict) -> None:
        sala = self.sala
        assert sala is not None and self.user_id is not None and self.seat is not None
        # (código, texto): el código es lo que traduce el front; el texto, el respaldo.
        error: tuple[str, str] | None = None

        try:
            if action == "add_bot":
                sala.add_bot(self.user_id)
            elif action == "remove_bot":
                sala.remove_bot(self.user_id)
            elif action == "start":
                sala.start(self.user_id)
            elif action == "leave":
                sala.leave(self.user_id)
                await _broadcast(sala)
                return
            elif sala.state is None:
                error = ("not_started", "La partida todavía no ha empezado")
            else:
                # Todo lo demás es del juego, y lo valida el juego.
                error = sala.juego.accion(sala.state, self.seat, mensaje)
        except SalaError as exc:
            error = (exc.code, str(exc))

        if error:
            codigo, texto = error
            await self.send(
                text_data=json.dumps({"type": "error", "code": codigo, "message": texto})
            )
        await _broadcast(sala)
        start_drive(sala)

    # ── Mensajes del channel layer ───────────────────────────────────────────

    async def room_state(self, event):
        payload = dict(event["payload"])
        payload["type"] = "state"
        payload["seat"] = event.get("seat")
        await self.send(text_data=json.dumps(payload))
