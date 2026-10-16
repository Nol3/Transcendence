"""Salas del Culo: crear, entrar, bots, empezar y los límites.

La sala es lo que hace que se pueda jugar «entre amigos»: alguien la crea, sale un código
corto y se lo pasa. Aquí se prueba ese recorrido y lo que tiene que impedir (entrar en
una sala llena, empezar sin gente, entrar en una partida ya empezada).
"""
import unittest

from apps.culo.rooms import (
    MAX_JUGADORES,
    MIN_JUGADORES,
    RoomError,
    RoomRegistry,
)


class SalaTests(unittest.TestCase):
    def setUp(self):
        self.registry = RoomRegistry()
        self.sala = self.registry.create(host_id=1)

    def test_el_codigo_se_puede_dictar_por_telefono(self):
        self.assertEqual(len(self.sala.code), 4)
        # Sin letras ni números que se confunden al decirlos en voz alta.
        for prohibido in "O0I1S5":
            self.assertNotIn(prohibido, self.sala.code)

    def test_los_codigos_no_se_repiten(self):
        codigos = {self.registry.create(host_id=i).code for i in range(50)}
        self.assertEqual(len(codigos), 50)

    def test_entrar_y_ver_la_sala(self):
        self.sala.join(1, "ana")
        self.sala.join(2, "luis")
        vista = self.sala.to_dict(viewer_id=1)
        self.assertEqual([p["username"] for p in vista["players"]], ["ana", "luis"])
        self.assertTrue(vista["isHost"])
        self.assertEqual(vista["status"], "lobby")
        self.assertFalse(self.sala.to_dict(viewer_id=2)["isHost"])

    def test_volver_a_entrar_no_duplica_el_asiento(self):
        self.sala.join(1, "ana")
        self.sala.join(2, "luis")
        self.sala.disconnect(2)
        self.assertFalse(self.sala.players[1].connected)

        self.sala.join(2, "luis")  # vuelve
        self.assertEqual(len(self.sala.players), 2)
        self.assertTrue(self.sala.players[1].connected)

    def test_no_cabe_mas_gente_de_la_cuenta(self):
        for i in range(MAX_JUGADORES):
            self.sala.join(i, f"j{i}")
        with self.assertRaises(RoomError):
            self.sala.join(99, "tarde")

    def test_solo_el_anfitrion_anade_y_quita_bots(self):
        self.sala.join(1, "ana")
        self.sala.join(2, "luis")
        with self.assertRaises(RoomError):
            self.sala.add_bot(host_id=2)

        self.sala.add_bot(host_id=1)
        self.assertEqual(len(self.sala.players), 3)
        self.assertTrue(self.sala.players[-1].is_bot)

        self.assertTrue(self.sala.remove_bot(host_id=1))
        self.assertEqual(len(self.sala.players), 2)

    def test_hacen_falta_tres_jugadores_para_empezar(self):
        self.sala.join(1, "ana")
        self.sala.join(2, "luis")
        with self.assertRaises(RoomError):
            self.sala.start(host_id=1)

        self.sala.add_bot(host_id=1)
        self.sala.start(host_id=1)
        self.assertEqual(self.sala.status, "playing")
        self.assertIsNotNone(self.sala.state)
        self.assertEqual(len(self.sala.state.players), MIN_JUGADORES)

    def test_no_se_puede_entrar_en_una_partida_empezada(self):
        self.sala.join(1, "ana")
        self.sala.join(2, "luis")
        self.sala.add_bot(host_id=1)
        self.sala.start(host_id=1)
        with self.assertRaises(RoomError):
            self.sala.join(3, "tarde")

    def test_quien_se_va_del_lobby_deja_su_asiento(self):
        self.sala.join(1, "ana")
        self.sala.join(2, "luis")
        self.sala.leave(2)
        self.assertEqual([p.username for p in self.sala.players], ["ana"])

    def test_si_se_va_el_anfitrion_la_sala_pasa_al_siguiente(self):
        self.sala.join(1, "ana")
        self.sala.join(2, "luis")
        self.sala.leave(1)
        self.assertEqual(self.sala.host_id, 2)
        self.assertEqual([p.username for p in self.sala.players], ["luis"])

    def test_jugando_el_asiento_se_guarda_por_si_vuelve(self):
        self.sala.join(1, "ana")
        self.sala.join(2, "luis")
        self.sala.add_bot(host_id=1)
        self.sala.start(host_id=1)

        self.sala.disconnect(2)
        self.assertEqual(len(self.sala.players), 3)  # sigue su asiento
        self.assertFalse(self.sala.players[1].connected)
        self.assertFalse(self.sala.state.players[1].connected)

    def test_la_conexion_vieja_no_echa_al_que_ya_ha_vuelto(self):
        """Recargar la página: la conexión nueva entra antes de que cierre la vieja.

        Sin la comprobación del canal, la sala daría por ido a un jugador que está
        dentro. Se reproduce el orden real: primero vuelve, luego se cae la antigua.
        """
        self.sala.join(1, "ana", channel="canal-viejo")
        self.sala.join(2, "luis", channel="canal-luis")
        self.sala.add_bot(host_id=1)
        self.sala.start(host_id=1)

        # Ana recarga: entra con un canal nuevo...
        self.sala.join(1, "ana", channel="canal-nuevo")
        self.assertTrue(self.sala.players[0].connected)

        # ...y solo después termina de cerrarse la conexión antigua.
        cambio = self.sala.disconnect(1, channel="canal-viejo")

        self.assertFalse(cambio, "no debería tocar nada: ya hay una conexión más nueva")
        self.assertTrue(self.sala.players[0].connected)
        self.assertTrue(self.sala.state.players[0].connected)
        self.assertEqual(self.sala.players[0].channel, "canal-nuevo")

        # Y cuando se cae la de verdad, sí se le da por ido.
        self.assertTrue(self.sala.disconnect(1, channel="canal-nuevo"))
        self.assertFalse(self.sala.players[0].connected)

    def test_la_vista_de_la_partida_es_la_de_cada_uno(self):
        self.sala.join(1, "ana")
        self.sala.join(2, "luis")
        self.sala.add_bot(host_id=1)
        self.sala.start(host_id=1)

        vista = self.sala.to_dict(viewer_id=1)
        self.assertIn("game", vista)
        manos = {p["id"]: p["hand"] for p in vista["game"]["players"]}
        # La mía entera; la de los demás, vacía (solo el número de cartas).
        self.assertTrue(manos[0])
        self.assertEqual(manos[1], [])
        self.assertEqual(manos[2], [])

    def test_las_salas_vacias_se_recogen(self):
        self.registry.create(host_id=2).join(2, "otro")
        self.assertEqual(len(self.registry.all()), 2)

        # Una sala sin nadie conectado y con el tiempo pasado se tira.
        self.sala.join(1, "ana")
        self.sala.disconnect(1)
        self.sala.touched -= 120
        self.assertEqual(self.registry.purge(), 1)
        self.assertIsNone(self.registry.get(self.sala.code))

    def test_buscar_una_sala_que_no_existe(self):
        self.assertIsNone(self.registry.get("ZZZZ"))
        self.assertIsNone(self.registry.get(""))
