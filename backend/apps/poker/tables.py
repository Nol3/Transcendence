"""Mesas: ciclo de vida de la partida, turnos, bots y expulsión por inactividad.

La mesa es la dueña del estado: nadie fuera del servidor puede mover fichas ni
ver cartas ajenas. Los temporizadores se apoyan en un contador de versión, de modo
que un temporizador obsoleto (porque el estado ya cambió) simplemente no hace nada.
"""
from __future__ import annotations

import asyncio
import json
import random
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from .bots import decide as bot_decide
from .engine import CHECK, FOLD, Hand, IllegalAction

DEFAULT_TURN_TIMEOUT = 25.0
DEFAULT_BOT_DELAY = 1.0
DEFAULT_NEXT_HAND_DELAY = 4.0


@dataclass
class TableSeat:
    index: int
    username: str
    stack: int
    user_id: int | None = None
    is_bot: bool = False
    connected: bool = False
    channel: str | None = None


class PokerTable:
    """Una partida heads-up (o de N asientos) que se juega mano a mano."""

    def __init__(
        self,
        table_id: str,
        seats: list[TableSeat],
        small_blind: int = 5,
        big_blind: int = 10,
        turn_timeout: float = DEFAULT_TURN_TIMEOUT,
        bot_delay: float = DEFAULT_BOT_DELAY,
        next_hand_delay: float = DEFAULT_NEXT_HAND_DELAY,
        max_hands: int | None = None,
        rng: random.Random | None = None,
        on_match_end: Callable[[PokerTable], Awaitable[None]] | None = None,
        context: dict | None = None,
    ):
        self.id = table_id
        self.seats = seats
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.turn_timeout = turn_timeout
        self.bot_delay = bot_delay
        self.next_hand_delay = next_hand_delay
        self.max_hands = max_hands
        self.rng = rng
        self.on_match_end = on_match_end
        # Metadatos de la mesa: hoy se usa para saber si la partida es de un match
        # de torneo ({"tournament_id": .., "match_id": ..}), lo que permite cerrar
        # el resultado desde el servidor en vez de esperar a que lo reporte nadie.
        self.context: dict = context or {}

        self.hand: Hand | None = None
        self.hand_number = 0
        self.button = 0
        self.version = 0
        self.finished = False
        self.winner: TableSeat | None = None
        self.log: list[dict] = []
        # Resumen de cada mano terminada; se persiste al acabar la partida
        # (historial). El motor ya lo calcula, aquí solo se copia.
        self.hands: list[dict] = []
        self._tasks: set[asyncio.Task] = set()

    # ── Consultas ────────────────────────────────────────────────────────────
    @property
    def humans(self) -> list[TableSeat]:
        return [s for s in self.seats if not s.is_bot]

    def seat_of_user(self, user_id: int | None) -> int | None:
        for s in self.seats:
            if s.user_id is not None and s.user_id == user_id:
                return s.index
        return None

    def snapshot(self, for_user_id: int | None = None) -> dict:
        idx = self.seat_of_user(for_user_id) if for_user_id is not None else None
        return {
            "type": "table_state",
            "table": {
                "id": self.id,
                "hand_number": self.hand_number,
                "finished": self.finished,
                "small_blind": self.small_blind,
                "big_blind": self.big_blind,
                "turn_timeout": self.turn_timeout,
                "winner": self.winner.username if self.winner else None,
            },
            "you": idx,
            "game": self.hand.state_for(idx) if self.hand else None,
            "log": self.log[-8:],
        }

    # ── Ciclo de vida ────────────────────────────────────────────────────────
    def start(self) -> None:
        """Arranca la primera mano (lo llama quien crea la mesa)."""
        self._start_hand()

    def _start_hand(self) -> None:
        if self.finished:
            return
        self.hand_number += 1
        if self.max_hands is not None and self.hand_number > self.max_hands:
            self._finish_match("se agotaron las manos")
            return
        if self.hand_number > 1:
            self.button = (self.button + 1) % len(self.seats)

        self.hand = Hand(
            stacks=[s.stack for s in self.seats],
            button=self.button,
            small_blind=self.small_blind,
            big_blind=self.big_blind,
            names=[s.username for s in self.seats],
            bots=[s.index for s in self.seats if s.is_bot],
            rng=self.rng,
        ).start()
        self.version += 1

    def _finish_match(self, reason: str) -> None:
        self.finished = True
        ranking = sorted(self.seats, key=lambda s: s.stack, reverse=True)
        # Empate: los dos mejores con el mismo stack no producen ganador.
        empatados = len(ranking) > 1 and ranking[0].stack == ranking[1].stack
        self.winner = None if empatados else ranking[0]
        self.log.append({"event": "match_end", "reason": reason,
                         "winner": self.winner.username if self.winner else None,
                         "stacks": [s.stack for s in self.seats]})
        self._cancel_tasks()
        self.version += 1

    def _match_over(self) -> bool:
        return any(s.stack <= 0 for s in self.seats)

    # ── Conexión ─────────────────────────────────────────────────────────────
    async def join(self, channel_name: str, user_id: int, username: str) -> bool:
        idx = self.seat_of_user(user_id)
        if idx is None:
            return False
        seat = self.seats[idx]
        seat.connected = True
        seat.channel = channel_name
        seat.username = username or seat.username
        # En las mesas que no arrancan solas (las de torneo), la primera mano se
        # reparte cuando están todos sentados: nadie pierde la ciega mientras el
        # rival todavía carga la página.
        if self.hand is None and all(s.connected or s.is_bot for s in self.seats):
            self.start()
        await self.broadcast()
        self._schedule_actor()
        return True

    async def leave(self, channel_name: str) -> None:
        for seat in self.seats:
            if seat.channel == channel_name:
                seat.connected = False
                seat.channel = None
                self.version += 1
                self._schedule_actor()   # si era su turno, arranca el temporizador
                break
        await self.broadcast()

    # ── Acciones ─────────────────────────────────────────────────────────────
    async def act(self, user_id: int, action: str, amount: int | None = None) -> None:
        if self.finished:
            raise ValueError("la partida ha terminado")
        if self.hand is None or self.hand.complete:
            raise ValueError("no hay una mano en juego")
        idx = self.seat_of_user(user_id)
        if idx is None:
            raise ValueError("no estás sentado en esta mesa")
        if self.hand.actor != idx:
            raise ValueError("no es tu turno")
        self.hand.act(idx, action, amount)
        self.version += 1
        await self._after_action()

    async def _after_action(self) -> None:
        assert self.hand is not None
        if self.hand.complete:
            self._sync_stacks()
            self.hands.append(self._hand_summary())
            self.log.append({"event": "hand_result", "hand_number": self.hand_number,
                             "result": self.hand.result})
            if self._match_over():
                self._finish_match("un jugador se quedó sin fichas")
                await self.broadcast()
                if self.on_match_end:
                    await self.on_match_end(self)
                return
            await self.broadcast()
            self._after(self.next_hand_delay, self._next_hand)
            return
        await self.broadcast()
        self._schedule_actor()

    def _hand_summary(self) -> dict:
        """Resumen de la mano recién terminada, listo para el historial.

        Se apoya en `Hand.result` (que ya trae tablero, botes, ganadores, cartas
        reveladas y stacks) y añade lo que solo sabe la mesa: qué usuario hay en
        cada asiento.
        """
        assert self.hand is not None
        res = self.hand.result or {}
        won: dict[int, int] = {}
        for pot in res.get("pots") or []:
            for w in pot.get("winners") or []:
                won[w["seat"]] = won.get(w["seat"], 0) + int(w.get("amount") or 0)

        revealed = res.get("revealed") or {}
        hand_names = res.get("hands") or {}
        stacks = res.get("stacks") or []

        jugadores = []
        for i, seat in enumerate(self.seats):
            hseat = self.hand.seats[i]
            cartas = revealed.get(i, revealed.get(str(i))) or []
            nombre_mano = (hand_names.get(i) or hand_names.get(str(i)) or {}).get("name", "")
            jugadores.append({
                "seat": i,
                "user_id": seat.user_id,
                "name": seat.username,
                "is_bot": seat.is_bot,
                "hole": " ".join(str(c) for c in cartas),
                "hand_name": nombre_mano,
                "stack_after": stacks[i] if i < len(stacks) else seat.stack,
                "won": won.get(i, 0),
                "folded": bool(getattr(hseat, "folded", False)),
            })

        return {
            "hand_number": self.hand_number,
            "board": " ".join(str(c) for c in (res.get("board") or [])),
            "pot": int(res.get("total") or 0),
            "showdown": bool(res.get("showdown")),
            "winner_names": ", ".join(j["name"] for j in jugadores if j["won"] > 0)[:200],
            "players": jugadores,
            # Registro de acciones de la mano, para poder reproducirla paso a paso
            # (roadmap 7.2). Se pasa por JSON para asegurar que es almacenable: el
            # motor va acumulando eventos y alguno podría llevar un objeto.
            "actions": json.loads(json.dumps(self.hand.history, default=str)),
        }

    def _sync_stacks(self) -> None:
        """Copia los stacks del motor a los asientos de la mesa al acabar la mano.

        Sin esto la mesa se quedaba con los stacks del inicio de la mano: nadie
        llegaba nunca a 0 fichas (la partida no terminaba) y **cada mano volvía a
        repartir el stack inicial**, así que el hook de fin de partida no se
        disparaba y no se registraba ni resultado ni ELO.
        """
        assert self.hand is not None
        for seat, hand_seat in zip(self.seats, self.hand.seats, strict=False):
            seat.stack = hand_seat.stack

    async def _next_hand(self) -> None:
        self._start_hand()
        await self.broadcast()
        if self.finished:            # se agotaron las manos: cerrar la partida
            if self.on_match_end:
                await self.on_match_end(self)
            return
        self._schedule_actor()

    # ── Turnos: bots e inactividad ───────────────────────────────────────────
    def _schedule_actor(self) -> None:
        if self.finished or self.hand is None or self.hand.complete:
            return
        idx = self.hand.actor
        if idx is None:
            return
        seat = self.seats[idx]
        if seat.is_bot:
            self._after(self.bot_delay, self._bot_turn)
        elif seat.connected:
            self._after(self.turn_timeout, self._timeout_turn)
        # Si el humano aún no está conectado, no se le penaliza: esperamos.

    async def _bot_turn(self) -> None:
        assert self.hand is not None
        idx = self.hand.actor
        if idx is None or not self.seats[idx].is_bot:
            return
        action, amount = bot_decide(self.hand, idx, self.rng)
        try:
            self.hand.act(idx, action, amount)
        except IllegalAction:
            options = self.hand.legal_actions(idx)
            pick = next(o for o in options if o["action"] in (CHECK, FOLD))
            self.hand.act(idx, pick["action"], pick.get("amount"))
        self.version += 1
        await self._after_action()

    async def _timeout_turn(self) -> None:
        assert self.hand is not None
        idx = self.hand.actor
        if idx is None:
            return
        options = {o["action"] for o in self.hand.legal_actions(idx)}
        action = CHECK if CHECK in options else FOLD
        self.hand.act(idx, action)
        self.log.append({"event": "timeout", "seat": idx, "action": action,
                         "hand_number": self.hand_number})
        self.version += 1
        await self._after_action()

    # ── Temporizadores con guarda de versión ─────────────────────────────────
    def _after(self, delay: float, factory) -> asyncio.Task:
        version = self.version

        async def runner():
            try:
                await asyncio.sleep(delay)
            except asyncio.CancelledError:
                return
            if version != self.version or self.finished:
                return          # el estado ya cambió: este temporizador está obsoleto
            await factory()

        task = asyncio.create_task(runner())
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    def _cancel_tasks(self) -> None:
        for task in list(self._tasks):
            task.cancel()
        self._tasks.clear()

    # ── Difusión personalizada ───────────────────────────────────────────────
    async def broadcast(self) -> None:
        """Envía a cada conexión SU vista (nadie recibe cartas ajenas)."""
        from channels.layers import get_channel_layer

        layer = get_channel_layer()
        if layer is None:
            return
        for seat in self.seats:
            if not seat.channel:
                continue
            await layer.send(seat.channel, {
                "type": "table.message",
                "payload": self.snapshot(seat.user_id),
            })
        # Espectadores: vista **sin asiento** (`you=None`), así que nunca ven cartas
        # ajenas salvo las que se revelan en el showdown. El grupo se deriva del id
        # de la mesa, no hace falta guardar estado extra.
        await layer.group_send(f"poker_spectators_{self.id}", {
            "type": "table.message",
            "payload": self.snapshot(None),
        })


class TableRegistry:
    """Registro de mesas vivas del proceso.

    Es deliberadamente simple: con el channel layer en memoria (una sola instancia
    de Daphne) es coherente. Para varias réplicas habrá que moverlo a Redis.
    """

    def __init__(self) -> None:
        self._tables: dict[str, PokerTable] = {}

    def create(self, seats: list[TableSeat], **kwargs) -> PokerTable:
        table_id = uuid.uuid4().hex[:12]
        table = PokerTable(table_id, seats, **kwargs)
        self._tables[table_id] = table
        return table

    def get(self, table_id: str) -> PokerTable | None:
        return self._tables.get(table_id)

    def drop(self, table_id: str) -> None:
        table = self._tables.pop(table_id, None)
        if table:
            table._cancel_tasks()

    def all(self) -> list[PokerTable]:
        return list(self._tables.values())


registry = TableRegistry()


def heads_up_seats(human: tuple[int, str], opponent: tuple[int | None, str], starting_stack: int,
                   bot: bool) -> list[TableSeat]:
    """Construye los dos asientos de una mesa heads-up."""
    return [
        TableSeat(index=0, user_id=human[0], username=human[1], stack=starting_stack),
        TableSeat(index=1, user_id=opponent[0], username=opponent[1], stack=starting_stack,
                  is_bot=bot),
    ]
