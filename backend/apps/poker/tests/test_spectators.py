"""Espectadores y chat de mesa (5.4).

Un espectador es una conexión **sin asiento**: recibe siempre la vista sin asiento
(`you=None`), así que no ve cartas ajenas fuera del showdown, y no puede actuar.
El chat de mesa son mensajes efímeros por el mismo WebSocket.
"""
import asyncio
import random

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from apps.poker.consumers import TableConsumer
from apps.poker.engine import Hand
from apps.poker.tables import PokerTable, TableSeat, registry
from apps.users.models import UserProfile


class FakeChannelLayer:
    """Registra lo que se envía a cada grupo."""

    def __init__(self):
        self.groups: list[tuple[str, dict]] = []

    async def group_send(self, group, message):
        self.groups.append((group, message))


class FakeConsumer:
    """Cliente mínimo para ejercitar `on_chat` sin levantar un WebSocket."""

    MAX_CHAT_LEN = TableConsumer.MAX_CHAT_LEN
    CHAT_COOLDOWN = TableConsumer.CHAT_COOLDOWN

    def __init__(self, username="ana", spectator=False):
        self.username = username
        self.spectator = spectator
        self.last_chat = 0.0
        self.group_name = "poker_abc"
        self.spectators_group = "poker_spectators_abc"
        self.channel_layer = FakeChannelLayer()
        self.errores: list[str] = []

    async def send_error(self, message):
        self.errores.append(message)

    async def on_chat(self, payload):
        return await TableConsumer.on_chat(self, payload)


def broadcast_groups(consumer):
    return [g for g, _ in consumer.channel_layer.groups]


class SpectatorViewTests(TestCase):
    """La vista sin asiento no filtra cartas privadas."""

    def setUp(self):
        self.hand = Hand(
            stacks=[100, 100], small_blind=5, big_blind=10,
            names=["ana", "luis"], rng=random.Random(3),
        ).start()

    def test_la_vista_de_espectador_no_tiene_asiento(self):
        vista = self.hand.state_for(None)
        self.assertNotIn("you", vista)          # state_for no marca asiento
        for asiento in vista["seats"]:
            self.assertIsNone(asiento["hole"], "un espectador no ve ninguna carta")

    def test_en_showdown_si_se_ven_las_cartas_reveladas(self):
        # Se juega la mano hasta el final con check/call para llegar al showdown.
        for _ in range(60):
            if self.hand.complete:
                break
            idx = self.hand.actor
            if idx is None:
                break
            opciones = {o["action"] for o in self.hand.legal_actions(idx)}
            accion = "check" if "check" in opciones else "call"
            self.hand.act(idx, accion)

        self.assertTrue(self.hand.complete)
        vista = self.hand.state_for(None)
        if self.hand.result and self.hand.result.get("showdown"):
            reveladas = [a["hole"] for a in vista["seats"]]
            self.assertTrue(any(h for h in reveladas), "en showdown sí se revelan")

    def test_la_vista_de_jugador_solo_le_enseña_sus_cartas(self):
        vista = self.hand.state_for(0)
        self.assertEqual(vista["seats"][0]["hole"], [str(c) for c in self.hand.seats[0].hole])
        self.assertIsNone(vista["seats"][1]["hole"])

    def test_un_espectador_no_puede_actuar(self):
        table = PokerTable("mesa-test", [
            TableSeat(index=0, user_id=1, username="ana", stack=100),
            TableSeat(index=1, user_id=2, username="luis", stack=100),
        ], small_blind=5, big_blind=10)
        table.start()
        with self.assertRaises(ValueError):
            asyncio.run(table.act(999, "call"))       # 999 no está sentado
        self.assertIsNone(table.seat_of_user(999))

    def test_la_mesa_manda_la_vista_de_espectador_al_grupo(self):
        layer = FakeChannelLayer()
        table = PokerTable("mesa-esp", [
            TableSeat(index=0, user_id=1, username="ana", stack=100),
            TableSeat(index=1, user_id=2, username="luis", stack=100),
        ], small_blind=5, big_blind=10)
        table.start()

        # Se sustituye el channel layer real por el falso.
        import channels.layers
        original = channels.layers.get_channel_layer
        channels.layers.get_channel_layer = lambda: layer
        try:
            asyncio.run(table.broadcast())
        finally:
            channels.layers.get_channel_layer = original

        grupos = [g for g, _ in layer.groups]
        self.assertIn("poker_spectators_mesa-esp", grupos)
        _, mensaje = layer.groups[0]
        self.assertEqual(mensaje["type"], "table.message")
        self.assertIsNone(mensaje["payload"]["you"], "la vista de espectador no tiene asiento")


class TableChatTests(TestCase):
    def test_un_mensaje_normal_se_difunde_a_jugadores_y_espectadores(self):
        consumer = FakeConsumer("ana")
        asyncio.run(consumer.on_chat({"text": "  hola mesa  "}))
        self.assertEqual(consumer.errores, [])
        self.assertEqual(len(consumer.channel_layer.groups), 2, "a los dos grupos")
        self.assertEqual(broadcast_groups(consumer),
                         ["poker_abc", "poker_spectators_abc"])
        _, mensaje = consumer.channel_layer.groups[0]
        payload = mensaje["payload"]
        self.assertEqual(payload["type"], "chat")
        self.assertEqual(payload["from"], "ana")
        self.assertEqual(payload["text"], "hola mesa")
        self.assertFalse(payload["spectator"])
        self.assertTrue(payload["at"])

    def test_un_espectador_tambien_puede_escribir(self):
        consumer = FakeConsumer("mirón", spectator=True)
        asyncio.run(consumer.on_chat({"text": "¡vaya mano!"}))
        _, mensaje = consumer.channel_layer.groups[0]
        self.assertTrue(mensaje["payload"]["spectator"])

    def test_un_mensaje_vacio_se_ignora(self):
        consumer = FakeConsumer()
        asyncio.run(consumer.on_chat({"text": "   "}))
        asyncio.run(consumer.on_chat({}))
        self.assertEqual(consumer.channel_layer.groups, [])
        self.assertEqual(consumer.errores, [])

    def test_un_mensaje_larguisimo_se_recorta(self):
        consumer = FakeConsumer()
        asyncio.run(consumer.on_chat({"text": "x" * 5000}))
        _, mensaje = consumer.channel_layer.groups[0]
        self.assertEqual(len(mensaje["payload"]["text"]), TableConsumer.MAX_CHAT_LEN)

    def test_escribir_muy_seguido_se_frena(self):
        consumer = FakeConsumer()
        asyncio.run(consumer.on_chat({"text": "primero"}))
        asyncio.run(consumer.on_chat({"text": "segundo"}))     # demasiado pronto
        self.assertEqual(len(consumer.channel_layer.groups), 2, "solo pasó el primero")
        self.assertTrue(consumer.errores, "debe avisar de que va rápido")


class LiveTablesTests(TestCase):
    def setUp(self):
        self.ana = User.objects.create_user("ana", "ana@example.com", "Zx9!pqLmn42")
        UserProfile.objects.get_or_create(user=self.ana)
        self.client = APIClient()
        self.client.force_authenticate(self.ana)

    def tearDown(self):
        for table in registry.all():
            registry.drop(table.id)

    def test_lista_las_mesas_vivas(self):
        table = registry.create([
            TableSeat(index=0, user_id=self.ana.id, username="ana", stack=100),
            TableSeat(index=1, username="Bot X", stack=100, is_bot=True),
        ], small_blind=5, big_blind=10)
        table.start()

        res = self.client.get("/api/poker/tables/")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertGreaterEqual(res.data["count"], 1)
        fila = next(m for m in res.data["results"] if m["table_id"] == table.id)
        self.assertEqual(fila["seats"], 2)
        self.assertEqual(fila["players"], ["ana", "Bot X"])
        self.assertFalse(fila["finished"])
        self.assertGreaterEqual(fila["hand_number"], 1)

    def test_sin_sesion_no_hay_lista(self):
        anon = APIClient()
        self.assertIn(anon.get("/api/poker/tables/").status_code, (401, 403))

    def test_las_mesas_terminadas_van_al_final(self):
        viva = registry.create([
            TableSeat(index=0, user_id=self.ana.id, username="ana", stack=100),
            TableSeat(index=1, username="Bot X", stack=100, is_bot=True),
        ], small_blind=5, big_blind=10)
        viva.start()

        acabada = registry.create([
            TableSeat(index=0, user_id=self.ana.id, username="ana", stack=100),
            TableSeat(index=1, username="Bot Y", stack=100, is_bot=True),
        ], small_blind=5, big_blind=10)
        acabada.start()
        acabada.seats[1].stack = 0
        acabada._finish_match("test")

        resultados = self.client.get("/api/poker/tables/").data["results"]
        posiciones = {m["table_id"]: i for i, m in enumerate(resultados)}
        self.assertLess(posiciones[viva.id], posiciones[acabada.id])
