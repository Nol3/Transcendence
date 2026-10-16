"""La sala del Mentiroso: lobby, arranque, acciones y WebSocket.

Se prueba la **capa genérica** (códigos, asientos, reconexión) usando el Mentiroso como juego, y
que el envoltorio de `juego.py` valide de verdad: el servidor es el que decide, así que una acción
imposible tiene que salir rechazada desde aquí y no desde el navegador.
"""
from __future__ import annotations

import json

from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.mentiroso.juego import MentirosoJuego
from apps.salas.juegos import JUEGOS
from apps.salas.juegos import get as get_juego

# El registro de verdad, el de módulo: es el que usa el consumidor del WebSocket. Con uno nuevo,
# la conexión no encontraría la sala (y el test fallaría por una razón que no es la del juego).
from apps.salas.rooms import SalaError, registry

User = get_user_model()
# Las cabeceras van como pares (nombre, valor): es lo que espera el validador de origen.
ORIGEN = [(b"origin", b"http://localhost")]


class SalaMentirosoTests(TestCase):
    def setUp(self):
        self.ana = User.objects.create_user(username="ana", email="ana@example.com", password="x")
        self.luis = User.objects.create_user(username="luis", email="luis@example.com", password="x")
        self.marta = User.objects.create_user(username="marta", email="marta@example.com", password="x")
        self.registry = registry
        registry.clear()
        self.addCleanup(registry.clear)

    def _sala(self, jugadores=3, **opciones):
        sala = self.registry.create(self.ana.id, "mentiroso", opciones)
        for u in (self.ana, self.luis, self.marta)[:jugadores]:
            sala.join(u.id, u.username)
        return sala

    # ── Lobby ────────────────────────────────────────────────────────────────

    def test_el_juego_se_registra_solo_al_arrancar(self):
        self.assertIn("mentiroso", JUEGOS)
        self.assertEqual(get_juego("mentiroso").min_jugadores, 3)

    def test_crear_sala_y_ver_el_lobby(self):
        sala = self._sala()
        self.assertEqual(len(sala.code), 4)
        vista = sala.to_dict(viewer_id=self.ana.id)
        self.assertEqual(vista["juego"], "mentiroso")
        self.assertEqual(vista["status"], "lobby")
        self.assertTrue(vista["isHost"])
        self.assertNotIn("game", vista)  # todavía no hay partida
        self.assertEqual([p["username"] for p in vista["players"]], ["ana", "luis", "marta"])

    def test_solo_el_anfitrion_empieza_y_anade_bots(self):
        sala = self._sala()
        with self.assertRaises(SalaError) as ctx:
            sala.start(self.luis.id)
        self.assertEqual(ctx.exception.code, "host_only")
        with self.assertRaises(SalaError):
            sala.add_bot(self.luis.id)

    def test_hacen_falta_tres_jugadores(self):
        sala = self.registry.create(self.ana.id, "mentiroso")
        sala.join(self.ana.id, self.ana.username)
        with self.assertRaises(SalaError) as ctx:
            sala.start(self.ana.id)
        self.assertEqual(ctx.exception.code, "min_players")

    def test_el_bot_llena_la_mesa_a_medias(self):
        sala = self._sala(2)
        sala.add_bot(self.ana.id)
        sala.start(self.ana.id)
        self.assertEqual(sala.status, "playing")
        self.assertTrue(sala.state.players[2].is_bot)

    def test_reconectar_no_duplica_el_asiento(self):
        sala = self._sala()
        sala.join(self.luis.id, self.luis.username)
        self.assertEqual(len(sala.players), 3)

    def test_una_conexion_vieja_no_echa_a_quien_ya_volvio(self):
        sala = self._sala()
        sala.start(self.ana.id)
        sala.join(self.luis.id, self.luis.username, channel="canal-nuevo")
        self.assertFalse(sala.disconnect(self.luis.id, channel="canal-viejo"))
        self.assertTrue(sala.players[1].connected)

    # ── La partida ───────────────────────────────────────────────────────────

    def test_la_vista_es_la_de_cada_uno(self):
        sala = self._sala()
        sala.start(self.ana.id)
        vista = sala.to_dict(viewer_id=self.luis.id)
        self.assertIn("game", vista)
        mio = next(p for p in vista["game"]["players"] if p["name"] == "luis")
        otro = next(p for p in vista["game"]["players"] if p["name"] == "ana")
        self.assertGreater(mio["handCount"], 0)
        self.assertEqual(len(vista["game"]["myHand"]), mio["handCount"])
        self.assertNotIn("hand", otro)  # de los demás solo se sabe cuántas llevan
        self.assertNotIn("pile", vista["game"])

    def test_el_juego_rechaza_lo_que_no_vale(self):
        juego = MentirosoJuego()
        sala = self._sala()
        sala.start(self.ana.id)
        estado = sala.state

        # Fuera de turno.
        error = juego.accion(estado, 1, {"action": "play", "cards": [], "claimedRank": 5})
        self.assertEqual(error[0], "not_your_turn")
        # Una carta que está en la mano de otro: el servidor no la acepta.
        ajena = estado.players[1].hand[0].id
        error = juego.accion(estado, 0, {"action": "play", "cards": [ajena], "claimedRank": 5})
        self.assertEqual(error[0], "not_your_card")
        # Y una acción que no existe.
        self.assertEqual(juego.accion(estado, 0, {"action": "volar"})[0], "unknown_action")

    def test_jugar_bien_y_desconfiar(self):
        juego = MentirosoJuego()
        sala = self._sala()
        sala.start(self.ana.id)
        estado = sala.state

        carta = estado.players[0].hand[0]
        self.assertIsNone(
            juego.accion(estado, 0, {"action": "play", "cards": [carta.id], "claimedRank": 5})
        )
        self.assertEqual(estado.claimed_rank, 5)
        self.assertEqual(estado.pile[-1].id, carta.id)

        # Marta desconfía (mentira o verdad, da igual): alguien se lleva el montón.
        self.assertIsNone(juego.accion(estado, 2, {"action": "challenge"}))
        self.assertEqual(len(estado.pile), 0)
        self.assertTrue(estado.events[-1]["kind"] == "take")

    def test_el_bot_juega_cuando_le_toca(self):
        juego = MentirosoJuego()
        sala = self._sala(2)
        sala.add_bot(self.ana.id)
        sala.start(self.ana.id)
        estado = sala.state

        # Se juega hasta que le toque al bot, y el bot tiene que mover ficha.
        vueltas = 0
        while juego.turno_de_bot(estado) is None and vueltas < 20:
            vueltas += 1
            carta = estado.players[estado.turn].hand[0]
            juego.accion(
                estado, estado.turn, {"action": "play", "cards": [carta.id], "claimedRank": 5}
            )
        seat = juego.turno_de_bot(estado)
        self.assertIsNotNone(seat, "el bot debería tener el turno en algún momento")
        antes = len(estado.pile)
        juego.jugar_bot(estado, seat)
        self.assertNotEqual(len(estado.pile), antes)  # ha jugado o ha hecho que alguien recoja

    def test_la_mano_siguiente_la_puede_pedir_cualquiera(self):
        juego = MentirosoJuego()
        sala = self._sala()
        sala.start(self.ana.id)
        estado = sala.state
        # Ana se descarga entera: gana la mano.
        juego.accion(
            estado, 0, {"action": "play", "cards": [c.id for c in estado.players[0].hand],
                        "claimedRank": 5}
        )
        self.assertEqual(estado.phase, "hand-end")
        self.assertIsNone(juego.accion(estado, 1, {"action": "next_hand"}))
        self.assertEqual(estado.phase, "playing")
        self.assertEqual(estado.hand, 2)
        self.assertEqual(estado.players[0].wins, 1)


class SalaApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="api", email="api@example.com", password="x"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        registry.clear()
        self.addCleanup(registry.clear)

    def test_crear_sala_por_api(self):
        res = self.client.post("/api/salas/", {"juego": "mentiroso"}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["juego"], "mentiroso")
        self.assertEqual(res.json()["minPlayers"], 3)
        self.assertEqual(res.json()["maxPlayers"], 6)

    def test_un_juego_que_no_existe_da_400_con_la_lista(self):
        res = self.client.post("/api/salas/", {"juego": "ajedrez"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("mentiroso", res.json()["juegos"])

    def test_mirar_y_entrar_en_una_sala(self):
        creada = self.client.post("/api/salas/", {"juego": "mentiroso"}, format="json").json()
        code = creada["code"]
        self.assertEqual(self.client.get(f"/api/salas/{code}/").status_code, 200)

        otro = User.objects.create_user(username="otro", email="otro@example.com", password="x")
        cliente = APIClient()
        cliente.force_authenticate(otro)
        res = cliente.post(f"/api/salas/{code}/join/", format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()["players"]), 2)

    def test_una_sala_que_no_existe_da_404(self):
        self.assertEqual(self.client.get("/api/salas/ZZZZ/").status_code, 404)

    def test_sin_sesion_no_se_puede_crear(self):
        self.assertEqual(APIClient().post("/api/salas/", {"juego": "mentiroso"}).status_code, 401)

    def test_la_lista_de_juegos_online(self):
        res = self.client.get("/api/salas/juegos/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("mentiroso", res.json())


class SalaWebSocketTests(TestCase):
    """Dos conexiones reales contra la app ASGI, como en el Culo."""

    def setUp(self):
        self.ana = User.objects.create_user(username="wsana", email="wsana@example.com", password="x")
        registry.clear()
        self.addCleanup(registry.clear)
        self.sala = registry.create(self.ana.id, "mentiroso")
        self.sala.join(self.ana.id, self.ana.username)
        # El token se crea aquí (contexto sync) porque los tests son async.
        self._tokens = {self.ana.pk: str(RefreshToken.for_user(self.ana).access_token)}

    def _token(self, user) -> str:
        """El JWT de ese usuario, ya creado por el `setUp`.

        No se crea aquí a propósito: `for_user` **escribe** en la tabla de tokens emitidos (la
        app del blacklist está puesta) y estos tests son `async`, así que desde ahí revienta con
        `SynchronousOnlyOperation`.
        """
        return self._tokens[user.pk]

    def test_sin_token_cierra_con_4401(self):
        from config.asgi import application

        async def correr():
            com = WebsocketCommunicator(
                application, f"/ws/salas/mentiroso/{self.sala.code}/", headers=ORIGEN
            )
            conectado, _ = await com.connect()
            return conectado, com

        conectado, _com = async_to_sync(correr)()
        # Nada de `disconnect()`: la conexión ya la cerró el servidor, y volver a cerrarla
        # revienta con CancelledError (y taparía el fallo de verdad si lo hubiera).
        self.assertFalse(conectado)

    def test_sala_que_no_existe_cierra(self):
        from config.asgi import application

        async def correr():
            com = WebsocketCommunicator(
                application,
                f"/ws/salas/mentiroso/ZZZZ/?token={self._token(self.ana)}",
                headers=ORIGEN,
            )
            conectado, codigo = await com.connect()
            return conectado, codigo, com

        conectado, codigo, _com = async_to_sync(correr)()
        self.assertFalse(conectado)
        self.assertEqual(codigo, 4404)

    def test_entrar_y_ver_el_lobby(self):
        from config.asgi import application

        async def correr():
            com = WebsocketCommunicator(
                application,
                f"/ws/salas/mentiroso/{self.sala.code}/?token={self._token(self.ana)}",
                headers=ORIGEN,
            )
            conectado, _ = await com.connect()
            if not conectado:
                return False, None
            mensaje = json.loads(await com.receive_from(timeout=5))
            await com.disconnect()
            return True, mensaje

        conectado, mensaje = async_to_sync(correr)()
        self.assertTrue(conectado)
        self.assertEqual(mensaje["type"], "state")
        self.assertEqual(mensaje["code"], self.sala.code)
        self.assertEqual(mensaje["juego"], "mentiroso")
        self.assertEqual(mensaje["players"][0]["username"], "wsana")
        self.assertEqual(mensaje["seat"], 0)

    def test_empezar_por_websocket_y_recibir_la_partida(self):
        from config.asgi import application

        self.sala.add_bot(self.ana.id)
        self.sala.add_bot(self.ana.id)

        async def correr():
            com = WebsocketCommunicator(
                application,
                f"/ws/salas/mentiroso/{self.sala.code}/?token={self._token(self.ana)}",
                headers=ORIGEN,
            )
            conectado, _ = await com.connect()
            if not conectado:
                return None
            await com.receive_from(timeout=5)  # el lobby
            await com.send_to(text_data=json.dumps({"action": "start"}))
            # Llegan el estado de la partida y, luego, los turnos de los bots.
            for _ in range(6):
                mensaje = json.loads(await com.receive_from(timeout=8))
                if mensaje.get("game"):
                    await com.disconnect()
                    return mensaje
            await com.disconnect()
            return None

        mensaje = async_to_sync(correr)()
        self.assertIsNotNone(mensaje, "debería llegar la partida repartida")
        self.assertEqual(mensaje["status"], "playing")
        self.assertIn("game", mensaje)
        self.assertGreater(len(mensaje["game"]["myHand"]), 0)
        self.assertEqual(len(mensaje["game"]["players"]), 3)

    def test_jugar_fuera_de_turno_se_rechaza_desde_el_servidor(self):
        from config.asgi import application

        self.sala.add_bot(self.ana.id)
        self.sala.add_bot(self.ana.id)

        async def correr():
            com = WebsocketCommunicator(
                application,
                f"/ws/salas/mentiroso/{self.sala.code}/?token={self._token(self.ana)}",
                headers=ORIGEN,
            )
            conectado, _ = await com.connect()
            if not conectado:
                return None
            await com.receive_from(timeout=5)
            await com.send_to(text_data=json.dumps({"action": "start"}))
            # Una jugada sin cartas: el servidor tiene que decir que no.
            await com.send_to(text_data=json.dumps({"action": "play", "cards": []}))
            for _ in range(8):
                mensaje = json.loads(await com.receive_from(timeout=8))
                if mensaje.get("type") == "error":
                    await com.disconnect()
                    return mensaje
            await com.disconnect()
            return None

        mensaje = async_to_sync(correr)()
        self.assertIsNotNone(mensaje, "una jugada sin cartas tiene que dar error")
        self.assertIn(mensaje["code"], ("no_cards", "not_your_turn"))
