"""Mesas de 3–6 jugadores: cola por tamaño, relleno con bots y regla de ELO.

El motor ya soportaba 2–6 asientos; lo que faltaba era poder **llenar** mesas
grandes desde la cola. Aquí se fijan las dos reglas nuevas:

- el emparejamiento es por (nivel de apuesta, tamaño de mesa): quien pide una mesa
  de 3 no se junta con quien pide una de 2;
- si no aparecen suficientes humanos, los huecos se cubren con bots.
"""
import json
from types import SimpleNamespace
from unittest.mock import patch as mock_patch

from asgiref.sync import async_to_sync
from django.contrib.auth.models import User
from django.test import TestCase

from apps.poker.consumers import TABLE_SIZES, PokerMatchmakingConsumer
from apps.poker.queue import InMemoryMatchQueue
from apps.poker.services import report_match_end
from apps.poker.tables import TableSeat, registry
from apps.users.models import UserProfile


class FakeQueueClient:
    """Cliente de cola mínimo: lo justo para ejercitar `_join_queue`."""

    def __init__(self, user_id, username, size=2, stake="low", queue=None):
        self.channel_name = f"chan-{username}"
        self.user_id = user_id
        self.username = username
        self.stake = stake
        self.size = size
        self.table_id = None
        self.queued = False
        self.queue_timer = None
        self.sent = []
        # La cola es compartida: es lo que hace que los clientes se vean entre sí.
        self.queue = queue or InMemoryMatchQueue()

    async def send(self, text_data=None, bytes_data=None):
        if text_data:
            self.sent.append(json.loads(text_data))

    async def _notify_match(self, channel, table, opponent, message):
        # Se reusa la implementación real salvo el envío por el channel layer.
        payload = {
            "type": "match_found",
            "table_id": table.id,
            "opponent": opponent,
            "seats": len(table.seats),
        }
        self.sent.append({**payload, "to": channel})

    async def _purge_dead(self):
        """La purga real; con clientes falsos solo caduca por tiempo."""
        await self.queue.purge()

    async def _remove_from_queue(self, channel):
        await self.queue.remove(channel)

    async def _bot_fallback(self):
        """Se usa la implementación real del temporizador de reserva."""
        return await PokerMatchmakingConsumer._bot_fallback(self)

    def _create_table(self, stake, humanos, bots):
        """Se usa la construcción real de la mesa."""
        return PokerMatchmakingConsumer._create_table(self, stake, humanos, bots)

    def mensajes(self, kind):
        return [m for m in self.sent if m.get("type") == kind]


async def join_queue(client):
    return await PokerMatchmakingConsumer._join_queue(client)


class MultiSeatQueueTests(TestCase):
    def setUp(self):
        self.queue = InMemoryMatchQueue()
        self.users = [
            User.objects.create_user(f"m{i}", f"m{i}@example.com", "Zx9!pqLmn42")
            for i in range(6)
        ]
        for u in self.users:
            UserProfile.objects.get_or_create(user=u)

    def tearDown(self):
        for table in registry.all():
            registry.drop(table.id)

    def _cliente(self, i, size=2):
        return FakeQueueClient(self.users[i].id, self.users[i].username, size=size,
                               queue=self.queue)

    # ── Emparejamiento ───────────────────────────────────────────────────────
    def test_tres_jugadores_que_piden_mesa_de_3_acaban_en_la_misma(self):
        a, b, c = (self._cliente(i, size=3) for i in range(3))
        async_to_sync(join_queue)(a)
        async_to_sync(join_queue)(b)
        async_to_sync(join_queue)(c)

        mesas = {m["table_id"] for cli in (a, b, c) for m in cli.mensajes("match_found")}
        self.assertEqual(len(mesas), 1, "los tres deben acabar en la misma mesa")
        table = registry.get(mesas.pop())
        self.assertEqual(len(table.seats), 3)
        self.assertEqual(sorted(s.user_id for s in table.seats),
                         sorted(u.id for u in self.users[:3]))
        self.assertFalse(any(s.is_bot for s in table.seats))

    def test_los_tamanos_de_mesa_no_se_mezclan(self):
        dos = self._cliente(0, size=2)
        tres = self._cliente(1, size=3)
        async_to_sync(join_queue)(dos)
        async_to_sync(join_queue)(tres)

        # El de mesa de 2 no empareja con el de mesa de 3: los dos esperan.
        self.assertEqual(dos.mensajes("match_found"), [])
        self.assertEqual(tres.mensajes("match_found"), [])
        self.assertTrue(dos.mensajes("searching"))
        self.assertEqual(async_to_sync(self.queue.count)(), 2)

    def test_sin_gente_suficiente_la_mesa_se_completa_con_bots(self):
        cliente = self._cliente(0, size=6)
        async_to_sync(join_queue)(cliente)

        # Se fuerza el temporizador de reserva sin esperar los segundos reales.
        cliente.queued = True
        with mock_patch("apps.poker.consumers.QUEUE_TIMEOUT", 0):
            async_to_sync(PokerMatchmakingConsumer._bot_fallback)(cliente)

        aviso = cliente.mensajes("match_found")
        self.assertTrue(aviso, "debe avisar de la mesa creada")
        table = registry.get(aviso[0]["table_id"])
        self.assertEqual(len(table.seats), 6)
        humanos = [s for s in table.seats if not s.is_bot]
        self.assertEqual(len(humanos), 1, "solo hay un humano en la cola")
        self.assertEqual(len([s for s in table.seats if s.is_bot]), 5)

    def test_el_tamano_de_mesa_invalido_se_rechaza(self):
        self.assertNotIn(7, TABLE_SIZES)
        self.assertEqual(len(TABLE_SIZES), 5)

    # ── La mesa grande se juega ──────────────────────────────────────────────
    def test_una_mesa_de_6_juega_una_mano_entera(self):
        """Un humano y cinco bots: la mano se completa y las fichas cuadran."""
        fake = SimpleNamespace()
        table = PokerMatchmakingConsumer._create_table(
            fake, "low",
            humanos=[(self.users[0].id, self.users[0].username, "chan-0")],
            bots=5,
        )
        self.assertEqual(len(table.seats), 6)
        table.seats[0].connected = True

        # Se juega con la lógica de bots hasta que la mano termina.
        for _ in range(400):
            if table.hand is None or table.hand.complete:
                break
            idx = table.hand.actor
            if idx is None:
                break
            from apps.poker.bots import decide

            accion, amount = decide(table.hand, idx, table.rng)
            table.hand.act(idx, accion, amount)

        self.assertTrue(table.hand.complete, "la mano debe cerrarse")
        # Conservación de fichas: nadie gana ni pierde fichas por arte de magia.
        self.assertEqual(sum(s.stack for s in table.hand.seats), 6 * 1000)
        # Y la mesa ha copiado esos stacks a sus asientos (sin esto, cada mano
        # volvía a repartir el stack inicial y la partida no terminaba nunca).
        self.assertEqual(sum(s.stack for s in table.seats), 6 * 1000)

    def test_la_partida_termina_cuando_alguien_se_queda_sin_fichas(self):
        """Regresión: sin copiar los stacks al acabar la mano, nadie llegaba a 0
        y el hook de fin de partida no se disparaba nunca."""
        terminadas = []

        async def hook(table):
            terminadas.append(table.id)

        table = registry.create(
            [
                TableSeat(index=0, user_id=self.users[0].id, username="a", stack=30),
                TableSeat(index=1, user_id=self.users[1].id, username="b", stack=30),
            ],
            small_blind=5, big_blind=10, on_match_end=hook,
        )
        table.start()

        for _ in range(300):
            if table.finished:
                break
            if table.hand is None or table.hand.complete:
                table._start_hand()
                continue
            idx = table.hand.actor
            if idx is None:
                break
            from apps.poker.bots import decide

            accion, amount = decide(table.hand, idx, table.rng)
            table.hand.act(idx, accion, amount)
            async_to_sync(table._after_action)()

        self.assertTrue(table.finished, "la partida debe acabar cuando alguien se arruina")
        self.assertIsNotNone(table.winner)
        self.assertEqual(terminadas, [table.id], "el hook de fin de partida debe dispararse")
        self.assertTrue(any(s.stack <= 0 for s in table.seats))
        self.assertEqual(sum(s.stack for s in table.seats), 60, "las fichas se conservan")

    # ── ELO ─────────────────────────────────────────────────────────────────
    def test_una_mesa_de_tres_humanos_no_mueve_el_elo(self):
        """El ELO del proyecto es 1v1: con 3+ humanos el resultado no puntúa."""
        fake = SimpleNamespace()
        table = PokerMatchmakingConsumer._create_table(
            fake, "low",
            humanos=[(u.id, u.username, f"chan-{i}") for i, u in enumerate(self.users[:3])],
            bots=0,
        )
        table.start()
        table.seats[1].stack = 0
        table.seats[2].stack = 0
        table._finish_match("test")

        from apps.games.models import Game

        async_to_sync(report_match_end)(table)
        game = Game.objects.order_by("-id").first()
        self.assertIsNotNone(game)
        self.assertFalse(game.rated, "una partida de 3 no debe mover el ELO")
        for user in self.users[:3]:
            user.profile.refresh_from_db()
            self.assertEqual(user.profile.elo_rating, 1600)
