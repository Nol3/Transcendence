"""Los dos WebSockets del póker, de punta a punta por la aplicación ASGI.

Los tests que había ejercitaban métodos del consumidor con dobles (`FakeConsumer`), así que
`connect`, `receive` y todo el consumidor de emparejamiento no se ejecutaban nunca: el módulo
estaba al 41 %. Aquí se habla WebSocket de verdad, con JWT en el query string, contra la app
ASGI real y un canal en memoria.

Lo que se fija, más allá de la cobertura:

- sin token (o con uno malo) no se entra, y el cierre es 4401;
- a una mesa que no existe, 4404;
- un espectador entra **sin asiento** y nunca ve cartas ajenas;
- las acciones se validan en el servidor: fuera de turno o con importe no numérico, error;
- el chat llega a los dos, se recorta a 200 y tiene freno anti-spam;
- el emparejamiento junta a dos que piden lo mismo, **no** mezcla tamaños de mesa distintos,
  y completa con bots cuando nadie aparece.
"""
from __future__ import annotations

import asyncio
import contextlib
from unittest.mock import patch

from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import User
from django.test import TestCase, TransactionTestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.poker.consumers import QUEUE_TIMEOUT, TableConsumer
from apps.poker.queue import InMemoryMatchQueue
from apps.poker.tables import TableSeat, registry
from config.asgi import application

ORIGEN = [(b"origin", b"http://localhost")]

_TOKENS: dict[int, str] = {}


def token_de(user) -> str:
    """El JWT ya creado en el `setUp`.

    No se crea aquí: `for_user` escribe en la tabla de tokens emitidos (blacklist) y estos
    tests son `async`, así que desde el bucle revienta con `SynchronousOnlyOperation`.
    """
    return _TOKENS[user.pk]


class BaseWebSocket(TransactionTestCase):
    def crear_usuarios(self, *nombres) -> list[User]:
        usuarios = [
            User.objects.create_user(n, f"{n}@example.com", "clave-de-prueba") for n in nombres
        ]
        _TOKENS.clear()
        for u in usuarios:
            _TOKENS[u.pk] = str(RefreshToken.for_user(u).access_token)
        return usuarios

    async def _conectar(self, url: str) -> WebsocketCommunicator:
        com = WebsocketCommunicator(application, url, headers=ORIGEN)
        conectado, _ = await com.connect()
        self.assertTrue(conectado, f"no se pudo conectar a {url}")
        return com

    async def _recibir(self, com, tipo: str, intentos: int = 8) -> dict:
        """Primer mensaje de ese tipo (los estados van llegando solos, en cualquier orden)."""
        for _ in range(intentos):
            mensaje = await asyncio.wait_for(com.receive_json_from(), timeout=5)
            if mensaje.get("type") == tipo:
                return mensaje
        self.fail(f"no llegó ningún mensaje de tipo {tipo!r}")

    async def _cerrar(self, *comunicadores) -> None:
        """Cierra las conexiones vaciando antes lo pendiente.

        Con varias pruebas `async` en el mismo proceso, cerrar dejando mensajes en la cola de
        salida revienta dentro de asgiref («Lock bound to a different event loop»), que es el
        mismo artefacto de la 3.7.2 que obligó a fijar esa versión. Vaciando primero, no pasa.
        """
        # `asyncio.CancelledError` **no** es una `Exception` (es `BaseException` desde Python
        # 3.8), así que `suppress(Exception)` no lo atrapaba: cuando el propio servidor ya cerró
        # la conexión —el freno del chat, por ejemplo— el `receive_nothing` de dentro se cancela
        # y el test reventaba al limpiar. Pasaba solo en serie; con `--parallel` el orden lo tapaba.
        silencio = contextlib.suppress(Exception, asyncio.CancelledError)
        for com in comunicadores:
            if not com.future.done():
                with silencio:
                    # Tope de 10: si la mesa sigue emitiendo estados, vaciar «hasta el infinito»
                    # colgaría el test; con unos pocos basta para que el cierre sea limpio.
                    for _ in range(10):
                        if com.output_queue.empty():
                            break
                        await com.receive_output()
            with silencio:
                await com.disconnect()

    async def _drenar(self, com) -> None:
        """Vacía lo que quede pendiente (estados de la mesa) antes de afirmar «no llega nada».

        Se mira la cola en vez de usar `receive_nothing`: en Python 3.11 cancelar el `get()` de
        la cola deja un waiter cancelado dentro, y la **siguiente** lectura del mismo
        comunicador revienta con `CancelledError` (el fallo que solo salía en el CI). En 3.12 lo
        limpian; aquí se evita el problema de raíz.
        """
        while not com.output_queue.empty():
            await com.receive_output()

    async def _nada(self, com, timeout: float = 0.2) -> bool:
        """`True` si en `timeout` segundos no ha llegado nada. Sin cancelar la cola."""
        await asyncio.sleep(timeout)
        return com.output_queue.empty()


class MesaWebSocketTests(BaseWebSocket):
    def setUp(self):
        registry.clear()
        self.ana, self.luis, self.mira = self.crear_usuarios("ana", "luis", "mira")
        self.mesa = registry.create(
            [
                TableSeat(index=0, user_id=self.ana.id, username="ana", stack=1000),
                TableSeat(index=1, user_id=self.luis.id, username="luis", stack=1000),
            ],
            small_blind=5,
            big_blind=10,
            turn_timeout=30,
        )
        self.mesa.start()

    def tearDown(self):
        registry.clear()

    async def test_sin_token_no_se_entra(self):
        com = WebsocketCommunicator(
            application, f"/ws/poker/table/{self.mesa.id}/", headers=ORIGEN
        )
        conectado, codigo = await com.connect()
        self.assertFalse(conectado)
        self.assertEqual(codigo, 4401)

    async def test_token_invalido_no_se_entra(self):
        com = WebsocketCommunicator(
            application, f"/ws/poker/table/{self.mesa.id}/?token=basura", headers=ORIGEN
        )
        conectado, codigo = await com.connect()
        self.assertFalse(conectado)
        self.assertEqual(codigo, 4401)

    async def test_mesa_que_no_existe(self):
        com = WebsocketCommunicator(
            application, f"/ws/poker/table/NOEXISTE/?token={token_de(self.ana)}", headers=ORIGEN
        )
        conectado, codigo = await com.connect()
        self.assertFalse(conectado)
        self.assertEqual(codigo, 4404)

    async def test_el_jugador_ve_su_asiento_y_sus_cartas(self):
        com = await self._conectar(f"/ws/poker/table/{self.mesa.id}/?token={token_de(self.ana)}")
        try:
            estado = await self._recibir(com, "table_state")
            self.assertEqual(estado["you"], 0)
            asientos = estado["game"]["seats"]
            self.assertEqual(len(asientos[0]["hole"]), 2)
            # Y no ve las del rival: su hueco viaja a `None` (solo se sabe cuántas tiene).
            self.assertIsNone(asientos[1]["hole"])
            self.assertEqual(asientos[1]["hole_count"], 2)
        finally:
            await self._cerrar(com)

    async def test_el_espectador_entra_sin_asiento(self):
        com = await self._conectar(f"/ws/poker/table/{self.mesa.id}/?token={token_de(self.mira)}")
        try:
            estado = await self._recibir(com, "table_state")
            self.assertIsNone(estado["you"])
            self.assertTrue(all(a["hole"] is None for a in estado["game"]["seats"]))
        finally:
            await self._cerrar(com)

    async def test_ping_responde_pong(self):
        com = await self._conectar(f"/ws/poker/table/{self.mesa.id}/?token={token_de(self.ana)}")
        try:
            await com.send_json_to({"type": "ping"})
            self.assertEqual((await self._recibir(com, "pong"))["type"], "pong")
        finally:
            await self._cerrar(com)

    async def test_un_mensaje_que_no_es_json_da_error(self):
        com = await self._conectar(f"/ws/poker/table/{self.mesa.id}/?token={token_de(self.ana)}")
        try:
            await com.send_to(text_data="{esto no es json")
            self.assertIn("no válido", (await self._recibir(com, "error"))["error"])
        finally:
            await self._cerrar(com)

    async def test_una_accion_sin_nombre_da_error(self):
        com = await self._conectar(f"/ws/poker/table/{self.mesa.id}/?token={token_de(self.ana)}")
        try:
            await com.send_json_to({"action": ""})
            self.assertIn("falta la acción", (await self._recibir(com, "error"))["error"])
        finally:
            await self._cerrar(com)

    async def test_un_importe_que_no_es_numero_da_error(self):
        com = await self._conectar(f"/ws/poker/table/{self.mesa.id}/?token={token_de(self.ana)}")
        try:
            await com.send_json_to({"action": "call", "amount": "mucho"})
            self.assertIn("importe no válido", (await self._recibir(com, "error"))["error"])
        finally:
            await self._cerrar(com)

    async def test_jugar_fuera_de_turno_se_rechaza_en_el_servidor(self):
        """El turno lo decide el motor, no el navegador."""
        turno = self.mesa.hand.actor
        fuera = self.luis if turno == 0 else self.ana
        com = await self._conectar(f"/ws/poker/table/{self.mesa.id}/?token={token_de(fuera)}")
        try:
            await com.send_json_to({"action": "call"})
            self.assertIn("no es tu turno", (await self._recibir(com, "error"))["error"])
        finally:
            await self._cerrar(com)

    async def test_el_turno_legal_mueve_la_mano(self):
        turno = self.mesa.hand.actor
        jugador = self.ana if turno == 0 else self.luis
        com = await self._conectar(f"/ws/poker/table/{self.mesa.id}/?token={token_de(jugador)}")
        try:
            await com.send_json_to({"action": "call"})
            # Tras la acción la mesa reparte estado nuevo; lo que no puede es llegar un error.
            estado = await self._recibir(com, "table_state")
            self.assertIn("game", estado)
            self.assertFalse(await self._nada(com, 0.2))
        finally:
            await self._cerrar(com)

    async def test_el_chat_llega_a_los_dos_y_dice_quien_lo_manda(self):
        c1 = await self._conectar(f"/ws/poker/table/{self.mesa.id}/?token={token_de(self.ana)}")
        c2 = await self._conectar(f"/ws/poker/table/{self.mesa.id}/?token={token_de(self.luis)}")
        try:
            await self._drenar(c1)
            await self._drenar(c2)
            await c1.send_json_to({"type": "chat", "text": "  hola mesa  "})
            for com in (c1, c2):
                mensaje = await self._recibir(com, "chat")
                self.assertEqual(mensaje["from"], "ana")
                self.assertEqual(mensaje["text"], "hola mesa")
                self.assertFalse(mensaje["spectator"])
        finally:
            await self._cerrar(c1, c2)

    # El recorte y el freno del chat se prueban en `ReglasDelChatTests`, sin socket ni reloj:
    # por WebSocket dependían de que el segundo mensaje llegara dentro de la ventana de 0,5 s, y
    # en el CI (Python 3.11 bajo `coverage`) no llegaba. Aquí queda lo que sí es del transporte.

    async def test_al_desconectar_se_libera_la_silla(self):
        com = await self._conectar(f"/ws/poker/table/{self.mesa.id}/?token={token_de(self.ana)}")
        # `connect()` acepta antes de que termine `join()`: el estado es la señal de que ya está.
        await self._recibir(com, "table_state")
        self.assertTrue(self.mesa.seats[0].connected)
        await self._cerrar(com)
        await asyncio.sleep(0.1)
        self.assertFalse(self.mesa.seats[0].connected)


class EmparejamientoWebSocketTests(BaseWebSocket):
    def setUp(self):
        registry.clear()
        self.ana, self.luis = self.crear_usuarios("ana", "luis")
        # Cola propia por test: la de verdad es un singleton del proceso y se contaminaría.
        self.cola = InMemoryMatchQueue()
        parche = patch("apps.poker.consumers.get_match_queue", return_value=self.cola)
        parche.start()
        self.addCleanup(parche.stop)

    def tearDown(self):
        registry.clear()

    async def test_al_entrar_manda_los_niveles_y_el_tamano(self):
        com = await self._conectar(f"/ws/poker/matchmaking?token={token_de(self.ana)}")
        try:
            listo = await self._recibir(com, "ready")
            self.assertIn("low", listo["stakes"])
            self.assertEqual(listo["table_sizes"], [2, 3, 4, 5, 6])
            self.assertEqual(listo["table_size"], 2)
            self.assertEqual(listo["queue_timeout"], QUEUE_TIMEOUT)
        finally:
            await self._cerrar(com)

    async def test_el_tamano_se_lee_del_query_y_lo_raro_cae_al_por_defecto(self):
        bueno = await self._conectar(f"/ws/poker/matchmaking?token={token_de(self.ana)}&size=4")
        malo = await self._conectar(f"/ws/poker/matchmaking?token={token_de(self.luis)}&size=99")
        try:
            self.assertEqual((await self._recibir(bueno, "ready"))["table_size"], 4)
            self.assertEqual((await self._recibir(malo, "ready"))["table_size"], 2)
        finally:
            await self._cerrar(bueno, malo)

    async def test_el_nivel_se_puede_cambiar_y_se_confirma(self):
        com = await self._conectar(f"/ws/poker/matchmaking?token={token_de(self.ana)}")
        try:
            await com.send_json_to({"type": "stake", "stake": "mid"})
            self.assertEqual((await self._recibir(com, "stake_set"))["stake"], "mid")
            # Un nivel inventado se ignora en silencio (no cambia nada).
            await com.send_json_to({"type": "stake", "stake": "gratis"})
            self.assertTrue(await self._nada(com, 0.2))
        finally:
            await self._cerrar(com)

    async def test_un_tamano_de_mesa_invalido_avisa(self):
        com = await self._conectar(f"/ws/poker/matchmaking?token={token_de(self.ana)}")
        try:
            await com.send_json_to({"type": "table_size", "size": 9})
            self.assertIn("no válido", (await self._recibir(com, "error"))["error"])
        finally:
            await self._cerrar(com)

    async def test_cancelar_saca_de_la_cola(self):
        com = await self._conectar(f"/ws/poker/matchmaking?token={token_de(self.ana)}")
        try:
            await self._recibir(com, "searching")
            self.assertEqual(len(await self.cola.entries()), 1)
            await com.send_json_to({"type": "cancel"})
            self.assertEqual((await self._recibir(com, "cancelled"))["type"], "cancelled")
            self.assertEqual(await self.cola.entries(), [])
        finally:
            await self._cerrar(com)

    async def test_ping_y_pong(self):
        com = await self._conectar(f"/ws/poker/matchmaking?token={token_de(self.ana)}")
        try:
            await com.send_json_to({"type": "ping"})
            self.assertEqual((await self._recibir(com, "pong"))["type"], "pong")
        finally:
            await self._cerrar(com)

    async def test_dos_que_piden_lo_mismo_acaban_en_la_misma_mesa(self):
        c1 = await self._conectar(f"/ws/poker/matchmaking?token={token_de(self.ana)}")
        try:
            await self._recibir(c1, "searching")
            c2 = await self._conectar(f"/ws/poker/matchmaking?token={token_de(self.luis)}")
            try:
                # Al segundo le llega directamente; al primero, por el canal.
                para_luis = await self._recibir(c2, "match_found")
                para_ana = await self._recibir(c1, "match_found")
                self.assertEqual(para_luis["table_id"], para_ana["table_id"])
                self.assertEqual(para_ana["opponent"], "luis")
                self.assertEqual(para_ana["seats"], 2)
                self.assertEqual(await self.cola.entries(), [])
                self.assertIsNotNone(registry.get(para_ana["table_id"]))
            finally:
                await self._cerrar(c2)
        finally:
            await c1.disconnect()

    async def test_tamanos_distintos_no_se_mezclan(self):
        c1 = await self._conectar(f"/ws/poker/matchmaking?token={token_de(self.ana)}&size=2")
        try:
            await self._recibir(c1, "searching")
            c2 = await self._conectar(f"/ws/poker/matchmaking?token={token_de(self.luis)}&size=6")
            try:
                await self._recibir(c2, "searching")
                self.assertTrue(await self._nada(c2, 0.3),
                                "uno que quiere mesa de 6 no puede caer en una de 2")
                self.assertEqual(len(await self.cola.entries()), 2)
            finally:
                await self._cerrar(c2)
        finally:
            await c1.disconnect()

    async def test_si_nadie_aparece_se_completa_con_bots(self):
        """El temporizador es el que hace que nunca te quedes mirando la cola."""
        with patch("apps.poker.consumers.QUEUE_TIMEOUT", 0.05):
            com = await self._conectar(f"/ws/poker/matchmaking?token={token_de(self.ana)}")
            try:
                self.assertEqual((await self._recibir(com, "searching"))["type"], "searching")
                encontrado = await self._recibir(com, "match_found")
                self.assertEqual(encontrado["seats"], 2)
                self.assertIn("bots", encontrado["message"])
                self.assertIsNotNone(registry.get(encontrado["table_id"]))
            finally:
                await self._cerrar(com)

    async def test_al_desconectar_sale_de_la_cola(self):
        com = await self._conectar(f"/ws/poker/matchmaking?token={token_de(self.ana)}")
        await self._recibir(com, "searching")
        await com.disconnect()
        await asyncio.sleep(0.1)
        self.assertEqual(await self.cola.entries(), [])

    async def test_cambiar_de_tamano_con_la_cola_abierta_reentra(self):
        com = await self._conectar(f"/ws/poker/matchmaking?token={token_de(self.ana)}")
        try:
            await self._recibir(com, "searching")
            await com.send_json_to({"type": "table_size", "size": 4})
            # Al cambiar de tamaño estando en cola, se sale y se vuelve a buscar.
            self.assertEqual((await self._recibir(com, "searching"))["table_size"], 4)
            entradas = await self.cola.entries()
            self.assertEqual([e["size"] for e in entradas], [4])
        finally:
            await self._cerrar(com)


class ReglasDelChatTests(TestCase):
    """El freno y el recorte del chat, **sin** socket ni reloj.

    Antes se probaban con dos mensajes seguidos por WebSocket, y eso depende de que el segundo
    llegue dentro de la ventana (0,5 s). En el CI —Python 3.11 bajo `coverage`— el segundo se
    procesaba más tarde, no se rechazaba (que es lo correcto) y además asgiref cerraba el
    comunicador antes de entregar la respuesta. La regla se prueba aquí, donde es determinista;
    el transporte sigue probado en `MesaWebSocketTests`.
    """

    class Capa:
        """Capa de canales de mentira: apunta lo que se manda a cada grupo."""

        def __init__(self) -> None:
            self.enviados: list[tuple[str, dict]] = []

        async def group_send(self, grupo: str, mensaje: dict) -> None:
            self.enviados.append((grupo, mensaje))

    def _consumidor(self):

        consumidor = TableConsumer()
        consumidor.username = "ana"
        consumidor.spectator = False
        consumidor.group_name = "mesa-1"
        consumidor.spectators_group = "mesa-1-espectadores"
        consumidor.channel_layer = self.Capa()
        consumidor.last_chat = 0.0
        consumidor.errores = []

        async def send_error(mensaje: str) -> None:
            consumidor.errores.append(mensaje)

        consumidor.send_error = send_error
        return consumidor

    def test_el_vacio_no_sale_el_largo_se_recorta_y_el_segundo_se_frena(self):
        consumidor = self._consumidor()

        async def escenario():
            await consumidor.on_chat({"text": "   "})
            vacio = list(consumidor.channel_layer.enviados)
            await consumidor.on_chat({"text": "x" * 500})
            await consumidor.on_chat({"text": "otra"})
            return vacio

        vacio = async_to_sync(escenario)()

        self.assertEqual(vacio, [], "un chat vacío no debe salir")
        self.assertEqual(len(consumidor.errores), 1, "el segundo mensaje seguido debe frenarse")
        self.assertIn("demasiado rápido", consumidor.errores[0])

        grupos = [grupo for grupo, _ in consumidor.channel_layer.enviados]
        self.assertEqual(grupos, ["mesa-1", "mesa-1-espectadores"])
        enviado = consumidor.channel_layer.enviados[0][1]["payload"]
        self.assertEqual(len(enviado["text"]), 200, "el mensaje largo se recorta")
        self.assertEqual(enviado["from"], "ana")
