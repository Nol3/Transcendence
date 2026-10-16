"""Salas del Culo: crear una, pasar el código a los amigos y jugar.

Una sala es efímera (no se guarda en base de datos): nace cuando alguien la crea, vive
mientras dura la partida y se tira cuando se queda vacía o pasa demasiado tiempo sin
movimiento. El código es corto y sin letras que se confunden al dictarlo por teléfono
(nada de O/0 ni I/1), porque el plan es justo ese: decírselo a alguien.
"""
from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field

from .engine import GameState, new_game

# Sin O/0, I/1, S/5: el código se dicta en voz alta.
ALFABETO = "ABCDEFGHJKLMNPQRTUVWXYZ2346789"
LARGO_CODIGO = 4
MAX_JUGADORES = 6
MIN_JUGADORES = 3  # el juego no tiene sentido con dos; con dos humanos entra un bot
MAX_BOTS = 5
# Una sala sin nadie conectado, o sin movimiento, se recoge.
VIDA_SALA = 3 * 3600


class RoomError(Exception):
    """Algo que impide entrar o seguir en la sala.

    Lleva un `code` corto (en inglés) para que el front lo traduzca, y el texto en español
    como respaldo legible si el código no se reconoce. Así la mesa habla el idioma del
    jugador sin que el servidor tenga que saber de traducciones.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass
class RoomPlayer:
    user_id: int | None
    username: str
    is_bot: bool = False
    connected: bool = True
    channel: str | None = None

    def to_dict(self) -> dict:
        return {
            "userId": self.user_id,
            "username": self.username,
            "isBot": self.is_bot,
            "connected": self.connected,
        }


@dataclass
class Room:
    code: str
    host_id: int
    decks: int = 1
    status: str = "lobby"  # lobby | playing | finished
    players: list[RoomPlayer] = field(default_factory=list)
    state: GameState | None = None
    touched: float = field(default_factory=time.time)

    # ── Lobby ────────────────────────────────────────────────────────────────

    def join(self, user_id: int, username: str, channel: str | None = None) -> RoomPlayer:
        """Entra en la sala (o vuelve a ella si ya estaba)."""
        self.touched = time.time()
        existente = next((p for p in self.players if p.user_id == user_id), None)
        if existente:
            # Reconexión: se queda con su asiento y sus cartas.
            existente.connected = True
            existente.channel = channel
            if self.state is not None:
                self.state.players[self.players.index(existente)].connected = True
            return existente

        if self.status != "lobby":
            raise RoomError("already_started", "La partida ya ha empezado")
        if len(self.players) >= MAX_JUGADORES:
            raise RoomError("room_full", "La sala está llena")
        jugador = RoomPlayer(user_id=user_id, username=username, channel=channel)
        self.players.append(jugador)
        return jugador

    def add_bot(self, host_id: int) -> RoomPlayer:
        self.touched = time.time()
        if host_id != self.host_id:
            raise RoomError("host_only", "Solo quien creó la sala puede añadir bots")
        if self.status != "lobby":
            raise RoomError("already_started", "La partida ya ha empezado")
        if len(self.players) >= MAX_JUGADORES:
            raise RoomError("room_full", "La sala está llena")
        n = sum(1 for p in self.players if p.is_bot) + 1
        bot = RoomPlayer(user_id=None, username=f"Bot {n}", is_bot=True)
        self.players.append(bot)
        return bot

    def remove_bot(self, host_id: int) -> bool:
        if host_id != self.host_id:
            raise RoomError("host_only", "Solo quien creó la sala puede quitar bots")
        bot = next((p for p in reversed(self.players) if p.is_bot), None)
        if not bot:
            return False
        self.players.remove(bot)
        self.touched = time.time()
        return True

    def leave(self, user_id: int) -> None:
        """Sale de la sala. En el lobby se va; jugando, se queda el asiento."""
        self.touched = time.time()
        jugador = next((p for p in self.players if p.user_id == user_id), None)
        if not jugador:
            return
        if self.status == "lobby":
            self.players.remove(jugador)
            # Si se va quien la creó, la sala pasa al siguiente.
            if user_id == self.host_id and self.players:
                siguiente = next((p for p in self.players if not p.is_bot), None)
                if siguiente and siguiente.user_id is not None:
                    self.host_id = siguiente.user_id
        else:
            jugador.connected = False
            if self.state is not None:
                self.state.players[self.players.index(jugador)].connected = False

    def disconnect(self, user_id: int, channel: str | None = None) -> bool:
        """Se ha caído una conexión: se guarda el asiento por si vuelve.

        Solo se marca desconectado si la que se ha caído es **la conexión actual**. Al
        recargar la página (o al volver del segundo plano en el móvil) la conexión nueva
        entra antes de que la vieja acabe de cerrarse; sin esta comprobación, la sala
        daría por ido a un jugador que está dentro. Devuelve si hubo cambio.
        """
        jugador = next((p for p in self.players if p.user_id == user_id), None)
        self.touched = time.time()
        if not jugador:
            return False
        if channel is not None and jugador.channel not in (None, channel):
            return False  # ya hay una conexión más nueva en ese asiento
        jugador.connected = False
        jugador.channel = None
        if self.state is not None:
            self.state.players[self.players.index(jugador)].connected = False
        return True

    def start(self, host_id: int) -> None:
        if host_id != self.host_id:
            raise RoomError("host_only", "Solo quien creó la sala puede empezar")
        if self.status != "lobby":
            raise RoomError("already_started", "La partida ya ha empezado")
        if len(self.players) < MIN_JUGADORES:
            raise RoomError("min_players", f"Hacen falta al menos {MIN_JUGADORES} jugadores")
        self.state = new_game(
            names=[p.username for p in self.players],
            bots=[p.is_bot for p in self.players],
            decks=self.decks,
        )
        self.status = "playing"
        self.touched = time.time()

    # ── Consultas ────────────────────────────────────────────────────────────

    @property
    def humans(self) -> list[RoomPlayer]:
        return [p for p in self.players if not p.is_bot]

    @property
    def empty(self) -> bool:
        return not any(p.connected and not p.is_bot for p in self.players)

    def seat_of(self, user_id: int) -> int | None:
        for i, p in enumerate(self.players):
            if p.user_id == user_id:
                return i
        return None

    def channel_of(self, seat: int) -> str | None:
        return self.players[seat].channel

    def to_dict(self, viewer_id: int | None = None) -> dict:
        """Estado de la sala para el lobby (y el de la partida si ya ha empezado)."""
        datos = {
            "code": self.code,
            "hostId": self.host_id,
            "status": self.status,
            "decks": self.decks,
            "players": [p.to_dict() for p in self.players],
            "isHost": viewer_id == self.host_id,
        }
        if self.state is not None and viewer_id is not None:
            from .engine import state_for

            # Ojo: el motor identifica a los jugadores por **asiento** (0, 1, 2…), no
            # por id de usuario. Aquí se traduce, que es justo donde se colaba el fallo
            # de que un jugador no viera su propia mano.
            datos["game"] = state_for(self.state, self.seat_of(viewer_id))
        return datos


class RoomRegistry:
    """Las salas que hay ahora mismo en este proceso.

    Igual que el registro de mesas del póker: vive en memoria, así que con varias
    réplicas de Daphne la sala la sirve el proceso donde se creó (ver `docs/ROADMAP.md`
    §4.1). Para el despliegue normal, con un backend, es suficiente.
    """

    def __init__(self) -> None:
        self._rooms: dict[str, Room] = {}

    def create(self, host_id: int, decks: int = 1) -> Room:
        self.purge()
        codigo = self._codigo_libre()
        sala = Room(code=codigo, host_id=host_id, decks=decks)
        self._rooms[codigo] = sala
        return sala

    def get(self, code: str) -> Room | None:
        return self._rooms.get((code or "").upper())

    def remove(self, code: str) -> None:
        self._rooms.pop((code or "").upper(), None)

    def all(self) -> list[Room]:
        return list(self._rooms.values())

    def clear(self) -> None:
        self._rooms.clear()

    def purge(self) -> int:
        """Tira las salas vacías o paradas. Devuelve cuántas."""
        ahora = time.time()
        fuera = [
            c for c, s in self._rooms.items()
            if (s.empty and ahora - s.touched > 60) or ahora - s.touched > VIDA_SALA
        ]
        for c in fuera:
            del self._rooms[c]
        return len(fuera)

    def _codigo_libre(self) -> str:
        for _ in range(50):
            codigo = "".join(secrets.choice(ALFABETO) for _ in range(LARGO_CODIGO))
            if codigo not in self._rooms:
                return codigo
        raise RoomError("no_codes", "No hay códigos libres, prueba otra vez")


registry = RoomRegistry()
