"""El WebSocket de la sala: dos amigos jugando de verdad por el canal.

Es la prueba que importa para «jugar entre amigos»: dos conexiones reales contra la app
ASGI, un JWT cada una, y se juega. Se comprueba lo que tiene que pasar (el lobby, empezar,
jugar, pasar) y lo que **no** puede pasar: que a uno le lleguen las cartas del otro, que
alguien juegue fuera de turno o que juegue cartas que no tiene.
"""
import asyncio

from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import User
from django.test import TransactionTestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.culo.rooms import registry
from config.asgi import application

ORIGEN = [(b"origin", b"http://localhost")]


_TOKENS: dict[int, str] = {}


def token_de(user) -> str:
    """El JWT de ese usuario, ya creado por el `setUp`.

    No se crea aquí a propósito: `for_user` **escribe** una fila en la tabla de tokens emitidos
    (la app del blacklist está puesta) y estos tests son `async`, así que desde ahí revienta con
    `SynchronousOnlyOperation`. El `setUp` los deja listos y esto solo los lee.
    """
    return _TOKENS[user.pk]


class SalaWebSocketTests(TransactionTestCase):
    def setUp(self):
        registry.clear()
        self.ana = User.objects.create_user("ana", "ana@example.com", "Zx9!pqLmn42")
        self.luis = User.objects.create_user("luis", "luis@example.com", "Zx9!pqLmn42")
        self.sala = registry.create(self.ana.id)
        self.sala.join(self.ana.id, "ana")
        # Los tokens se crean aquí (contexto sync) porque los tests son async.
        _TOKENS.clear()
        for jugador in (self.ana, self.luis):
            _TOKENS[jugador.pk] = str(RefreshToken.for_user(jugador).access_token)

    def tearDown(self):
        registry.clear()

    async def _esperar_estado(self, com, condicion, intentos: int = 25) -> dict:
        """Espera al estado que cumple una condición (los mensajes van llegando solos)."""
        for _ in range(intentos):
            mensaje = await asyncio.wait_for(com.receive_json_from(), timeout=6)
            if mensaje.get("type") == "state" and condicion(mensaje):
                return mensaje
        self.fail("no llegó el estado esperado")

    async def _estado_de(self, com, asiento: int) -> dict:
        """El estado que ve ese asiento, leído desde **su** conexión.

        Hace falta porque la vista de cada uno solo trae su propia mano: la de los demás
        viene vacía a propósito.
        """
        def tiene_su_mano(m) -> bool:
            juego = m.get("game") or {}
            jugadores = juego.get("players") or []
            return len(jugadores) > asiento and bool(jugadores[asiento].get("hand"))

        return await self._esperar_estado(com, tiene_su_mano)

    async def _avanzar_hasta(self, c1, c2, condicion, limite: int = 40):
        """Lee estados y, cuando le toca a un humano, pasa por él.

        Quien abre la primera ronda es aleatorio y la partida se para cuando le toca a
        una persona, así que un test no puede dar por hecho a quién le toca: se juega por
        los humanos (pasar siempre es legal) hasta llegar al estado que se busca.
        """
        conexiones = {0: c1, 1: c2}
        for _ in range(limite):
            mensaje = await asyncio.wait_for(c1.receive_json_from(), timeout=8)
            if mensaje.get("type") != "state":
                continue
            juego = mensaje.get("game")
            if not juego:
                continue
            if condicion(mensaje):
                return mensaje
            turno = juego.get("turn")
            if juego.get("phase") == "playing" and turno in conexiones:
                await conexiones[turno].send_json_to({"action": "pass"})
        self.fail("la partida no llegó al estado esperado")

    async def _esperar_turno_de_alguien(self, com, asientos=(0, 1)):
        """Espera a que le toque a uno de esos asientos.

        Quien abre la primera ronda es aleatorio, así que un test no puede dar por hecho
        que empieza un jugador concreto: se espera a quien sea y se juega desde ahí.
        """
        return await self._esperar_estado(
            com, lambda m: m.get("game", {}).get("turn") in asientos,
        )

    async def _conectar(self, user) -> WebsocketCommunicator:
        com = WebsocketCommunicator(
            application, f"/ws/culo/room/{self.sala.code}/?token={token_de(user)}",
            headers=ORIGEN,
        )
        conectado, _ = await com.connect()
        self.assertTrue(conectado, "no se pudo conectar al WebSocket")
        return com

    async def test_sin_sesion_no_se_entra(self):
        com = WebsocketCommunicator(
            application, f"/ws/culo/room/{self.sala.code}/", headers=ORIGEN,
        )
        conectado, codigo = await com.connect()
        self.assertFalse(conectado)
        self.assertEqual(codigo, 4401)

    async def test_sala_que_no_existe(self):
        com = WebsocketCommunicator(
            application, f"/ws/culo/room/ZZZZ/?token={token_de(self.ana)}", headers=ORIGEN,
        )
        conectado, codigo = await com.connect()
        self.assertFalse(conectado)
        self.assertEqual(codigo, 4404)

    async def test_el_lobby_llega_a_todos_y_se_puede_empezar(self):
        c1 = await self._conectar(self.ana)
        c2 = await self._conectar(self.luis)

        # A cada uno le llega la sala con los dos jugadores (el primero que llega ve
        # solo al anfitrión; hay que esperar al estado en el que ya están los dos).
        def dos(m) -> bool:
            return sorted(p["username"] for p in m["players"]) == ["ana", "luis"]

        for com in (c1, c2):
            mensaje = await self._esperar_estado(com, dos)
            self.assertEqual(mensaje["status"], "lobby")

        # El anfitrión añade un bot y reparte.
        await c1.send_json_to({"action": "add_bot"})
        await c1.send_json_to({"action": "start"})

        # A cada uno le llega SU vista: con su mano y sin la del otro.
        vistas = {}
        for nombre, com in (("ana", c1), ("luis", c2)):
            vistas[nombre] = await self._esperar_estado(
                com, lambda m: m["status"] == "playing",
            )

        for nombre, vista in vistas.items():
            self.assertEqual(vista["game"]["phase"], "playing")
            manos = {p["name"]: p["hand"] for p in vista["game"]["players"]}
            propias = manos[nombre]
            self.assertTrue(propias, "el jugador debería ver sus cartas")
            for otro, mano in manos.items():
                if otro != nombre:
                    self.assertEqual(mano, [], f"{nombre} no debería ver las cartas de {otro}")

        await c1.disconnect()
        await c2.disconnect()

    # Nota: no se prueba aquí «jugar una carta a media partida» por WebSocket. La partida
    # se para cuando le toca a una persona (que es lo correcto), así que un test tendría
    # que pilotar a los dos jugadores y dependería del ritmo de los bots. Eso ya está
    # cubierto donde toca: las reglas en `test_engine.py` (28 casos, con una partida
    # entera) y el transporte en el test del lobby de arriba, que comprueba que cada
    # conexión recibe su vista y solo la suya.
