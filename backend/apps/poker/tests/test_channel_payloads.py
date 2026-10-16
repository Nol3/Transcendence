"""Todo lo que viaja por el channel layer tiene que ser serializable.

Con `InMemoryChannelLayer` (una sola instancia) los mensajes **no se serializan**, así
que un diccionario con claves enteras pasaba sin problema. Con Redis, `channels_redis`
serializa con **msgpack** y msgpack rechaza las claves que no son de texto
(`int is not allowed for map key`): la conexión del jugador se caía con un 1011 justo
al llegar el showdown.

Estos tests son el guardián de esa clase de fallo: recorren los payloads reales
(resultado de la mano, estado por asiento y log de la mesa) y comprueban (1) que
ninguna clave de diccionario es un entero y (2) que msgpack los empaqueta y
desempaqueta.
"""
import asyncio
import random

import msgpack
from asgiref.sync import async_to_sync
from django.test import SimpleTestCase

from apps.poker.engine import ALL_IN, CALL, CHECK, Hand
from apps.poker.tables import PokerTable, TableSeat
from apps.poker.tests.helpers import build_deck


def hand(stacks, holes, board="", sb=5, bb=10):
    """Mano determinista con el mazo preparado (mismo patrón que test_game)."""
    deck = build_deck(holes, board, len(stacks))
    return Hand(stacks=list(stacks), button=0, small_blind=sb, big_blind=bb,
                deck_cards=deck).start()


def claves_no_texto(dato, ruta="raíz"):
    """Devuelve las rutas donde un diccionario tiene una clave que no es str."""
    malas = []
    if isinstance(dato, dict):
        for clave, valor in dato.items():
            if not isinstance(clave, str):
                malas.append(f"{ruta} → clave {clave!r} ({type(clave).__name__})")
            malas.extend(claves_no_texto(valor, f"{ruta}.{clave}"))
    elif isinstance(dato, (list, tuple)):
        for i, valor in enumerate(dato):
            malas.extend(claves_no_texto(valor, f"{ruta}[{i}]"))
    return malas


def serializa(dato) -> dict:
    """Empaqueta y desempaqueta como hace channels_redis (msgpack, strict_map_key)."""
    return msgpack.unpackb(msgpack.packb(dato), strict_map_key=True, raw=False)


class PayloadDelMotorTests(SimpleTestCase):
    """El resultado y el estado de una mano, tal cual salen del motor."""

    def _showdown(self) -> Hand:
        h = hand([1000, 1000], {0: "As Ad", 1: "Ks Kd"}, "2h 4d 6c 8s Td")
        h.act(0, CALL)
        h.act(1, CHECK)
        for _ in range(3):
            h.act(1, CHECK)
            h.act(0, CHECK)
        return h

    def test_el_showdown_no_usa_claves_enteras(self):
        h = self._showdown()
        self.assertTrue(h.complete)
        self.assertTrue(h.result["showdown"])
        # Las dos partes que se arreglaron: cartas reveladas y nombres de mano.
        self.assertEqual(sorted(h.result["revealed"]), ["0", "1"])
        self.assertEqual(sorted(h.result["hands"]), ["0", "1"])
        self.assertEqual(claves_no_texto(h.result), [])

    def test_en_el_showdown_los_demas_ven_las_cartas_reveladas(self):
        """El espectador y el rival tienen que ver las cartas, no `null`.

        Este caso se escapó al pasar `revealed` a claves de texto: la vista seguía
        buscando con el índice entero y devolvía la mano oculta.
        """
        h = self._showdown()
        vista_rival = h.state_for(0)["seats"][1]
        self.assertEqual(vista_rival["hole"], ["Ks", "Kd"])
        # Y la vista sin asiento (espectador) también.
        vista_espectador = h.state_for(None)["seats"][1]
        self.assertEqual(vista_espectador["hole"], ["Ks", "Kd"])

    def test_el_estado_de_cada_asiento_es_serializable(self):
        h = self._showdown()
        for asiento in (0, 1, None):
            estado = h.state_for(asiento)
            self.assertEqual(claves_no_texto(estado), [], f"asiento {asiento}")
            self.assertIsInstance(serializa(estado), dict)

    def test_una_retirada_tambien_es_serializable(self):
        h = hand([1000, 1000], {0: "As Kd", 1: "7c 8h"}, "2c 3d 4h 9s Tc")
        h.act(0, ALL_IN)
        h.act(1, CALL)
        estado = h.state_for(0)
        self.assertEqual(claves_no_texto(estado), [])
        self.assertIsInstance(serializa(estado), dict)


class PayloadDeLaMesaTests(SimpleTestCase):
    """Lo que la mesa manda de verdad: el estado con su log.

    Se usa `async_to_sync` (como el resto de los tests del póker) en vez de
    `IsolatedAsyncioTestCase`, que espera a que no quede ninguna tarea viva: la mesa
    deja temporizadores programados a propósito y el teardown se quedaría colgado.
    """

    def _table(self, **kwargs) -> PokerTable:
        seats = [TableSeat(index=0, user_id=1, username="Humano", stack=100),
                 TableSeat(index=1, username="Bot Nol3", stack=100, is_bot=True)]
        defaults = dict(small_blind=5, big_blind=10, turn_timeout=0.05,
                        bot_delay=0.001, next_hand_delay=0.02, rng=random.Random(3))
        defaults.update(kwargs)
        table = PokerTable("test-serializable", seats, **defaults)
        table.start()
        return table

    @staticmethod
    async def _jugar(table: PokerTable, hasta_el_final: bool) -> None:
        """Conecta al humano y deja correr la mesa **dentro del mismo bucle**.

        `async_to_sync` abre un bucle y lo cierra al volver: si se llamara solo al
        `join`, los temporizadores de la mesa morirían con él. Por eso el join y la
        espera van juntos en una sola corrutina.
        """
        await table.join("chan-humano", 1, "Humano")
        vueltas = 600 if hasta_el_final else 3
        for _ in range(vueltas):
            if table.finished:
                break
            await asyncio.sleep(0.02)

    def test_el_estado_de_la_mesa_con_log_pasa_por_msgpack(self):
        table = self._table(max_hands=4)
        try:
            async_to_sync(self._jugar)(table, True)
            self.assertTrue(table.finished, "la mesa debería cerrarse sola")

            # Lo mismo que se envía al cliente (y por tanto lo que cruza el layer).
            payload = {
                "type": "table_state",
                "you": 0,
                "table": {"id": table.id, "hand_number": table.hand_number,
                          "finished": table.finished, "winner": None},
                "game": table.snapshot(for_user_id=1),
                "log": table.log[-8:],
            }
            self.assertEqual(claves_no_texto(payload), [])
            self.assertIsInstance(serializa(payload), dict)
            # El log incluye el resultado de cada mano jugada.
            self.assertTrue(any(ev.get("event") == "hand_result" for ev in table.log))
        finally:
            table._cancel_tasks()

    def test_el_estado_en_curso_tambien_es_serializable(self):
        table = self._table()
        try:
            async_to_sync(self._jugar)(table, False)
            for usuario in (1, None):
                estado = table.snapshot(for_user_id=usuario)
                self.assertEqual(claves_no_texto(estado), [], f"usuario {usuario}")
                self.assertIsInstance(serializa(estado), dict)
        finally:
            table._cancel_tasks()
