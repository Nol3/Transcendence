"""WebSocket de la sala del Culo: `/ws/culo/room/<código>?token=...`

El servidor es el que decide. Todo lo que llega del cliente son **peticiones** (`jugar`,
`pasar`, `empezar`…): el motor valida el turno y la jugada contra el estado real, y cada
conexión recibe **su** vista, así que las cartas de los demás no salen de aquí.

Los bots juegan solos, con una pausa entre turnos para que se pueda seguir la partida, y
si a alguien se le cae la conexión se le guarda el asiento (y se pasa por él) para que
pueda volver a entrar.
"""
from __future__ import annotations

import asyncio
import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from apps.users.ws_auth import authenticate_ws

from .bots import bot_decision
from .engine import Card, do_pass, next_round, play
from .rooms import Room, RoomError, registry

# Pausa entre turnos de bot: se juega solo, pero a ritmo de persona.
BOT_DELAY = 0.9
# Si le toca a alguien desconectado, se le espera esto antes de pasar por él.
DESCONECTADO_TIMEOUT = 20.0

# Códigos de cierre propios, para que el cliente sepa qué ha pasado.
CLOSE_SIN_SESION = 4401
CLOSE_SALA_NO_EXISTE = 4404
CLOSE_SALA_LLENA = 4409


def _group(code: str) -> str:
    return f"culo_{code}"


async def _broadcast(room: Room) -> None:
    """Envía a cada jugador su propia vista de la sala (y de la partida)."""
    from channels.layers import get_channel_layer

    layer = get_channel_layer()
    if layer is None:
        return
    for i, jugador in enumerate(room.players):
        if jugador.is_bot or not jugador.channel:
            continue
        await layer.send(jugador.channel, {
            "type": "room.state",
            "payload": room.to_dict(viewer_id=jugador.user_id),
            "seat": i,
        })


def start_drive(room: Room) -> None:
    """Arranca (si no está ya) el avance automático de la partida.

    Se guarda la tarea en la propia sala para poder pararla cuando no queda nadie: si no,
    quedaría un bucle de bots corriendo por una sala que ya no existe.
    """
    tarea = getattr(room, "_drive_task", None)
    if tarea is not None and not tarea.done():
        return
    room._drive_task = asyncio.create_task(_drive(room))  # type: ignore[attr-defined]


async def _drive(room: Room) -> None:
    """Hace avanzar la partida sola: turnos de bot y turnos de quien no está.

    Se llama tras cada jugada. Va turno a turno hasta que le toca a alguien que está
    conectado, que es quien tiene que decidir.
    """
    if getattr(room, "_driving", False):
        return
    room._driving = True  # type: ignore[attr-defined]
    try:
        while room.status == "playing" and room.state is not None:
            seat = room.state.turn
            jugador = room.players[seat]

            if jugador.is_bot:
                await asyncio.sleep(BOT_DELAY)
                if room.status != "playing" or room.state is None or room.state.turn != seat:
                    return
                decision = bot_decision(room.state, seat)
                if decision:
                    play(room.state, seat, decision)
                else:
                    do_pass(room.state, seat)
                await _broadcast(room)
                continue

            if not jugador.connected:
                # Se le da un margen por si se le ha caído el wifi y vuelve.
                await asyncio.sleep(DESCONECTADO_TIMEOUT)
                if room.state is None or room.state.turn != seat:
                    return
                if room.players[seat].connected:
                    return  # ha vuelto: que juegue
                do_pass(room.state, seat)
                await _broadcast(room)
                continue

            return  # le toca a una persona conectada: aquí se para
    except asyncio.CancelledError:
        # La sala se ha quedado sin nadie: se para sin ruido.
        pass
    finally:
        room._driving = False  # type: ignore[attr-defined]


class CuloConsumer(AsyncWebsocketConsumer):
    """Una conexión = un asiento de una sala."""

    room: Room | None = None
    user_id: int | None = None
    seat: int | None = None

    async def connect(self):
        self.code = self.scope["url_route"]["kwargs"]["code"].upper()
        # La validación del JWT consulta la base de datos, y eso no se puede hacer desde
        # código async: se manda a un hilo (mismo patrón que la mesa de póker).
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
        except RoomError as exc:
            await self.accept()
            await self.send(
                text_data=json.dumps({"type": "error", "code": exc.code, "message": str(exc)})
            )
            await self.close(code=CLOSE_SALA_LLENA)
            return

        self.room = sala
        self.seat = sala.seat_of(self.user_id)
        await self.channel_layer.group_add(_group(self.code), self.channel_name)
        await self.accept()
        await _broadcast(sala)
        # Si la partida ya estaba en marcha, puede que le toque a un bot.
        start_drive(sala)

    async def disconnect(self, close_code):
        sala = self.room
        if sala is not None and self.user_id is not None:
            # Se le pasa el canal para no dar por ido a quien ya ha vuelto con otra
            # conexión (recarga de página, móvil que vuelve del segundo plano).
            if sala.disconnect(self.user_id, self.channel_name):
                await _broadcast(sala)
            # Si ya no queda nadie, se para el avance automático de la partida.
            if sala.empty:
                tarea = getattr(sala, "_drive_task", None)
                if tarea is not None and not tarea.done():
                    tarea.cancel()
        await self.channel_layer.group_discard(_group(self.code), self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if self.room is None or self.user_id is None or self.seat is None:
            return
        try:
            mensaje = json.loads(text_data or "{}")
        except json.JSONDecodeError:
            return
        await self._handle(mensaje.get("action"), mensaje)

    # ── Acciones ─────────────────────────────────────────────────────────────

    async def _handle(self, action, mensaje: dict) -> None:
        sala = self.room
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
            elif action == "play":
                error = self._jugar(mensaje.get("cards") or [])
            elif action == "pass":
                if sala.state is None or not do_pass(sala.state, self.seat):
                    error = ("not_your_turn", "Ahora no te toca")
            elif action == "next_round":
                if sala.state is None or sala.state.phase != "round-end":
                    error = ("round_not_over", "La ronda no ha terminado")
                elif self.user_id != sala.host_id:
                    error = ("host_only", "Solo quien creó la sala pasa de ronda")
                else:
                    next_round(sala.state)
            else:
                error = ("unknown_action", "Acción desconocida")
        except RoomError as exc:
            error = (exc.code, str(exc))

        if error:
            codigo, texto = error
            await self.send(
                text_data=json.dumps({"type": "error", "code": codigo, "message": texto})
            )
        await _broadcast(sala)
        start_drive(sala)

    def _jugar(self, ids: list[str]) -> str | None:
        """Valida y aplica una jugada. Devuelve el motivo si no vale."""
        sala = self.room
        assert sala is not None and sala.state is not None and self.seat is not None
        por_id = {c.id: c for c in sala.state.players[self.seat].hand}
        cartas: list[Card] = []
        for ident in ids:
            carta = por_id.get(ident)
            if carta is None:
                return "Esa carta no está en tu mano"
            cartas.append(carta)
        if not play(sala.state, self.seat, cartas):
            return "Esa jugada no vale ahora mismo"
        return None

    # ── Mensajes del channel layer ───────────────────────────────────────────

    async def room_state(self, event):
        payload = dict(event["payload"])
        payload["type"] = "state"
        payload["seat"] = event.get("seat")
        await self.send(text_data=json.dumps(payload))
