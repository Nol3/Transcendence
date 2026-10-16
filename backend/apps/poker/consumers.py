"""WebSockets del póker: mesa autoritativa y matchmaking con reserva de bot.

- `TableConsumer`            → `/ws/poker/table/<id>`   (la partida en sí)
- `PokerMatchmakingConsumer` → `/ws/poker/matchmaking`  (cola de espera)

Todo lo que llega del cliente son **peticiones**: el servidor valida el turno, la
acción y el importe contra el estado real. Cada conexión recibe su propia vista, así
que las cartas ajenas nunca salen del servidor.

Nota de escalado: la **cola de emparejamiento** vive en Redis cuando hay `REDIS_URL`
(`apps/poker/queue.py`), así que dos jugadores conectados a réplicas distintas se
emparejan. El **registro de mesas** sigue siendo del proceso que creó la mesa: con
varias réplicas, la mesa la sirve el proceso donde cayó el emparejamiento (ver
`docs/ROADMAP.md` §4.1).
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from urllib.parse import parse_qs

from channels.generic.websocket import AsyncWebsocketConsumer

from .engine import IllegalAction
from .queue import get_match_queue
from .tables import PokerTable, TableSeat, registry

# Niveles de apuesta disponibles (ciega pequeña, ciega grande, stack inicial).
STAKE_LEVELS = {
    "micro": {"small_blind": 1, "big_blind": 2, "starting_stack": 200},
    "low": {"small_blind": 5, "big_blind": 10, "starting_stack": 1000},
    "mid": {"small_blind": 25, "big_blind": 50, "starting_stack": 5000},
}
DEFAULT_STAKE = "low"

# Segundos que se espera a un humano antes de completar la mesa con un bot.
QUEUE_TIMEOUT = float(os.environ.get("POKER_QUEUE_TIMEOUT", "15"))
# Tiempo máximo por turno antes de pasar/foldear automáticamente.
TURN_TIMEOUT = float(os.environ.get("POKER_TURN_TIMEOUT", "25"))
BOT_NAMES = ("Bot Nol3", "Bot Málaga", "Bot 42", "Bot Rivera", "Bot Alborán")

# Tamaños de mesa admitidos (el motor soporta 2–6 asientos).
TABLE_SIZES = (2, 3, 4, 5, 6)
DEFAULT_TABLE_SIZE = 2


def _authenticate_sync(scope) -> tuple[int, str] | None:
    """Valida el JWT del query string y devuelve (id, username)."""
    token = (parse_qs(scope.get("query_string", b"").decode()).get("token") or [None])[0]
    if not token:
        return None
    try:
        from rest_framework_simplejwt.authentication import JWTAuthentication

        auth = JWTAuthentication()
        validated = auth.get_validated_token(token)
        user = auth.get_user(validated)
        return (user.id, user.username)
    except Exception:
        return None


class AuthedConsumer(AsyncWebsocketConsumer):
    """Autenticación por JWT en el query string (mismo patrón que el torneo)."""

    async def authenticate(self) -> bool:
        from asgiref.sync import sync_to_async

        result = await sync_to_async(_authenticate_sync, thread_sensitive=True)(self.scope)
        if result is None:
            await self.close(code=4401)
            return False
        self.user_id, self.username = result
        return True


class TableConsumer(AuthedConsumer):
    """Mesa autoritativa: reparte el estado y valida cada acción."""

    #: Longitud máxima de un mensaje de chat de mesa.
    MAX_CHAT_LEN = 200
    #: Segundos mínimos entre mensajes de la misma conexión (anti-spam básico).
    CHAT_COOLDOWN = 0.5

    async def connect(self):
        if not await self.authenticate():
            return
        self.table_id = self.scope["url_route"]["kwargs"]["table_id"]
        self.table: PokerTable | None = registry.get(self.table_id)
        if self.table is None:
            await self.close(code=4404)
            return

        # Sin asiento = **espectador**: puede mirar (y escribir en el chat de mesa),
        # pero no actuar; recibe siempre la vista sin asiento.
        self.spectator = self.table.seat_of_user(self.user_id) is None
        self.last_chat = 0.0
        self.group_name = f"poker_{self.table_id}"
        self.spectators_group = f"poker_spectators_{self.table_id}"

        await self.accept()
        await self.channel_layer.group_add(
            self.spectators_group if self.spectator else self.group_name,
            self.channel_name,
        )
        if self.spectator:
            # Estado actual para que no vea la mesa vacía hasta la siguiente mano.
            await self.send(text_data=json.dumps(self.table.snapshot(None)))
        else:
            # La lógica del motor es síncrona y sin E/S: se puede llamar directamente.
            await self.table.join(self.channel_name, self.user_id, self.username)

    async def disconnect(self, close_code):
        if getattr(self, "table", None) is not None and not getattr(self, "spectator", True):
            await self.table.leave(self.channel_name)
        if getattr(self, "group_name", None):
            await self.channel_layer.group_discard(
                self.spectators_group if getattr(self, "spectator", False) else self.group_name,
                self.channel_name,
            )

    async def receive(self, text_data=None, bytes_data=None):
        try:
            payload = json.loads(text_data) if text_data else {}
        except json.JSONDecodeError:
            await self.send_error("mensaje no válido")
            return

        if payload.get("type") == "ping":
            await self.send(text_data=json.dumps({"type": "pong"}))
            return

        if payload.get("type") == "chat":
            await self.on_chat(payload)
            return

        action = payload.get("action")
        if not action:
            await self.send_error("falta la acción")
            return
        amount = payload.get("amount")
        if amount is not None:
            try:
                amount = int(amount)
            except (TypeError, ValueError):
                await self.send_error("importe no válido")
                return

        try:
            await self.table.act(self.user_id, str(action), amount)
        except (IllegalAction, ValueError) as exc:
            await self.send_error(str(exc))

    async def on_chat(self, payload: dict) -> None:
        """Chat de mesa: mensajes efímeros, sin base de datos.

        Lo ven jugadores y espectadores de esa mesa. Se recorta la longitud y se
        limita la frecuencia por conexión para que nadie inunde la mesa.
        """
        texto = str(payload.get("text") or "").strip()
        if not texto:
            return
        texto = texto[: self.MAX_CHAT_LEN]

        ahora = time.time()
        if ahora - self.last_chat < self.CHAT_COOLDOWN:
            await self.send_error("vas demasiado rápido: espera un momento")
            return
        self.last_chat = ahora

        mensaje = {
            "type": "chat",
            "from": self.username,
            "spectator": bool(getattr(self, "spectator", False)),
            "text": texto,
            "at": time.strftime("%H:%M", time.localtime(ahora)),
        }
        for grupo in (self.group_name, self.spectators_group):
            await self.channel_layer.group_send(
                grupo, {"type": "table.message", "payload": mensaje}
            )

    async def send_error(self, message: str) -> None:
        await self.send(text_data=json.dumps({"type": "error", "error": message}))

    async def table_message(self, event):
        await self.send(text_data=json.dumps(event["payload"]))


class PokerMatchmakingConsumer(AuthedConsumer):
    """Cola de espera: empareja con un humano o, tras el tiempo máximo, con un bot.

    La cola la pone `get_match_queue()`: en memoria con una sola instancia de Daphne,
    en Redis en cuanto hay varias réplicas.
    """

    async def connect(self):
        if not await self.authenticate():
            return
        self.stake = DEFAULT_STAKE
        # El tamaño de mesa se fija ANTES de entrar en la cola (query string): si se
        # cambiara después, dos clientes que quieren mesa de 6 podrían emparejarse
        # como heads-up al coincidir en la cola.
        self.size = self._size_from_query()
        self.table_id: str | None = None
        self.queue_timer: asyncio.Task | None = None
        self.queued = False
        self.queue = get_match_queue()
        await self.accept()
        await self.send(text_data=json.dumps({
            "type": "ready",
            "stakes": {k: v for k, v in STAKE_LEVELS.items()},
            "table_sizes": list(TABLE_SIZES),
            "table_size": self.size,
            "queue_timeout": QUEUE_TIMEOUT,
            "turn_timeout": TURN_TIMEOUT,
        }))
        await self._join_queue()

    def _size_from_query(self) -> int:
        """Tamaño de mesa pedido en `?size=N` (2–6); por defecto, heads-up."""
        raw = (parse_qs(self.scope.get("query_string", b"").decode()).get("size") or [None])[0]
        try:
            size = int(raw) if raw is not None else DEFAULT_TABLE_SIZE
        except (TypeError, ValueError):
            return DEFAULT_TABLE_SIZE
        return size if size in TABLE_SIZES else DEFAULT_TABLE_SIZE

    # ── Cola ─────────────────────────────────────────────────────────────────
    async def _join_queue(self) -> None:
        """Entra en la cola y, si hay gente suficiente, abre la mesa.

        El emparejamiento es por **(nivel de apuesta, tamaño de mesa)**: quien pide
        una mesa de 6 solo se junta con otros que también la piden. Hacen falta
        `size - 1` compañeros; si no aparecen, el temporizador completa la mesa con
        bots.
        """
        await self._purge_dead()
        faltan = self.size - 1
        candidatos = [
            e for e in await self.queue.entries()
            if e["channel"] != self.channel_name
            and e.get("stake", DEFAULT_STAKE) == self.stake
            and e.get("size", DEFAULT_TABLE_SIZE) == self.size
        ]

        if len(candidatos) >= faltan:
            grupo = candidatos[:faltan]
            for entrada in grupo:
                await self.queue.remove(entrada["channel"])
            humanos = [(self.user_id, self.username, self.channel_name)] + [
                (e["user_id"], e["username"], e["channel"]) for e in grupo
            ]
            table = self._create_table(stake=self.stake, humanos=humanos, bots=0)
            nombres = ", ".join(n for _, n, _ in humanos[1:])
            for _, _, canal in humanos:
                await self._notify_match(canal, table, nombres,
                                         f"Emparejado con {nombres}")
            self.table_id = table.id
        else:
            await self.queue.join({
                "channel": self.channel_name,
                "user_id": self.user_id,
                "username": self.username,
                "stake": self.stake,
                "size": self.size,
            })
            self.queued = True
            await self.send(text_data=json.dumps({
                "type": "searching",
                "queue_timeout": QUEUE_TIMEOUT,
                "table_size": self.size,
                "message": "Buscando rival… si tarda, jugarás contra un bot."
                            if self.size == 2 else
                            f"Buscando {self.size - 1} jugadores más… los huecos que "
                            "queden se llenarán con bots.",
            }))
            self.queue_timer = asyncio.create_task(self._bot_fallback())

    async def _bot_fallback(self) -> None:
        """Si nadie aparece en QUEUE_TIMEOUT segundos, se completa con un bot."""
        try:
            await asyncio.sleep(QUEUE_TIMEOUT)
        except asyncio.CancelledError:
            return
        if self.table_id is not None or not self.queued:
            return
        await self.queue.remove(self.channel_name)
        self.queued = False

        # Se aprovechan los que sigan esperando el mismo tipo de mesa (sin llegar a
        # completarla) y el resto se cubre con bots.
        faltan = self.size - 1
        companeros = [
            e for e in await self.queue.entries()
            if e.get("stake", DEFAULT_STAKE) == self.stake
            and e.get("size", DEFAULT_TABLE_SIZE) == self.size
        ][:faltan]
        for entrada in companeros:
            await self.queue.remove(entrada["channel"])

        humanos = [(self.user_id, self.username, self.channel_name)] + [
            (e["user_id"], e["username"], e["channel"]) for e in companeros
        ]
        bots = self.size - len(humanos)
        table = self._create_table(stake=self.stake, humanos=humanos, bots=bots)
        nombres = ", ".join(n for _, n, _ in humanos[1:]) or "los bots"
        for _, _, canal in humanos:
            await self._notify_match(canal, table, nombres,
                                     "Nadie apareció: completamos la mesa con bots")

    def _create_table(self, stake: str, humanos: list[tuple], bots: int) -> PokerTable:
        """Mesa de `len(humanos) + bots` asientos (de 2 a 6)."""
        level = STAKE_LEVELS.get(stake, STAKE_LEVELS[DEFAULT_STAKE])
        seats = [
            TableSeat(index=i, user_id=user_id, username=username,
                      stack=level["starting_stack"])
            for i, (user_id, username, _canal) in enumerate(humanos)
        ]
        for j in range(bots):
            seats.append(TableSeat(
                index=len(seats),
                username=BOT_NAMES[(len(seats) + j) % len(BOT_NAMES)],
                stack=level["starting_stack"],
                is_bot=True,
            ))
        from .services import report_match_end

        table = registry.create(
            seats,
            small_blind=level["small_blind"],
            big_blind=level["big_blind"],
            turn_timeout=TURN_TIMEOUT,
            on_match_end=report_match_end,
        )
        table.start()
        return table

    async def _notify_match(self, channel: str, table: PokerTable, opponent: str,
                            message: str) -> None:
        payload = {
            "type": "match_found",
            "table_id": table.id,
            "opponent": opponent,
            "seats": len(table.seats),
            "small_blind": table.small_blind,
            "big_blind": table.big_blind,
            "turn_timeout": table.turn_timeout,
            "message": message,
        }
        if channel == self.channel_name:
            self.table_id = table.id
            await self.send(text_data=json.dumps(payload))
        else:
            await self.channel_layer.send(channel, {
                "type": "matchmaking.message", "payload": payload,
            })

    # ── Utilidades ───────────────────────────────────────────────────────────
    async def _remove_from_queue(self, channel: str) -> None:
        await self.queue.remove(channel)

    async def _purge_dead(self) -> None:
        """Descarta entradas caducadas (las de conexiones que ya no existen)."""
        await self.queue.purge()

    async def receive(self, text_data=None, bytes_data=None):
        try:
            payload = json.loads(text_data) if text_data else {}
        except json.JSONDecodeError:
            return
        kind = payload.get("type")
        if kind == "stake" and payload.get("stake") in STAKE_LEVELS:
            self.stake = payload["stake"]
            await self.send(text_data=json.dumps({"type": "stake_set", "stake": self.stake}))
        elif kind == "table_size":
            try:
                size = int(payload.get("size"))
            except (TypeError, ValueError):
                size = DEFAULT_TABLE_SIZE
            if size not in TABLE_SIZES:
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "error": f"tamaño de mesa no válido (usa {list(TABLE_SIZES)})",
                }))
                return
            self.size = size
            # Cambiar de tamaño con la cola abierta: se sale y se vuelve a entrar.
            if self.queued:
                await self._remove_from_queue(self.channel_name)
                if self.queue_timer:
                    self.queue_timer.cancel()
                self.queued = False
                await self._join_queue()
            else:
                await self.send(text_data=json.dumps(
                    {"type": "table_size_set", "table_size": size}
                ))
        elif kind == "cancel":
            self.queued = False
            await self._remove_from_queue(self.channel_name)
            if self.queue_timer:
                self.queue_timer.cancel()
            await self.send(text_data=json.dumps({"type": "cancelled"}))
        elif kind == "ping":
            await self.send(text_data=json.dumps({"type": "pong"}))

    async def disconnect(self, close_code):
        self.queued = False
        await self._remove_from_queue(self.channel_name)
        if self.queue_timer:
            self.queue_timer.cancel()

    async def matchmaking_message(self, event):
        payload = event["payload"]
        if payload.get("type") == "match_found":
            self.table_id = payload["table_id"]
            self.queued = False
            if self.queue_timer:
                self.queue_timer.cancel()
        await self.send(text_data=json.dumps(payload))
