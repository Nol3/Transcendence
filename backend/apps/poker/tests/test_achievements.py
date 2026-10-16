"""Logros del póker (roadmap 7.1).

Se calculan sobre el historial ya guardado, así que aquí se crean manos a mano (con
`PokerHandRecord` + `PokerHandPlayer`) en vez de jugar partidas enteras: así cada caso
—primera mano, escalera de color, racha— queda aislado y se lee de un vistazo.
"""
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from apps.poker.achievements import ESCALERA_DE_COLOR, logros_de, mejor_racha
from apps.poker.models import PokerHandPlayer, PokerHandRecord
from apps.users.models import UserProfile


def mano(numero, jugador, gano=0, hand_name="", con_rival=True):
    """Crea una mano con el jugador sentado en el asiento 0."""
    record = PokerHandRecord.objects.create(
        table_id="test", hand_number=numero, pot=100, showdown=True,
    )
    PokerHandPlayer.objects.create(
        hand=record, user=jugador, seat=0, name=jugador.username,
        hand_name=hand_name, won=gano,
    )
    if con_rival:
        PokerHandPlayer.objects.create(
            hand=record, seat=1, name="Bot Test", is_bot=True,
            won=0 if gano else 100,
        )
    return record


class LogrosCalculoTests(TestCase):
    def setUp(self):
        self.ana = User.objects.create_user("ana", "ana@example.com", "Zx9!pqLmn42")
        UserProfile.objects.get_or_create(user=self.ana)

    def _estado(self, logro_id):
        for logro in logros_de(self.ana):
            if logro["id"] == logro_id:
                return logro
        raise AssertionError(f"no existe el logro {logro_id}")

    def test_sin_manos_no_hay_ningun_logro(self):
        logros = logros_de(self.ana)
        self.assertEqual(len(logros), 3)
        self.assertFalse(any(logro["unlocked"] for logro in logros))
        self.assertEqual(self._estado("tres_seguidas")["progress"], 0)

    def test_ganar_una_mano_desbloquea_la_primera(self):
        mano(1, self.ana, gano=100)
        self.assertTrue(self._estado("primera_mano")["unlocked"])
        # …pero la racha de tres todavía no.
        self.assertFalse(self._estado("tres_seguidas")["unlocked"])
        self.assertEqual(self._estado("tres_seguidas")["progress"], 1)

    def test_perder_no_desbloquea_nada(self):
        mano(1, self.ana, gano=0)
        self.assertFalse(self._estado("primera_mano")["unlocked"])

    def test_una_escalera_de_color_desbloquea_su_logro(self):
        mano(1, self.ana, gano=100, hand_name=ESCALERA_DE_COLOR)
        self.assertTrue(self._estado("escalera_de_color")["unlocked"])

    def test_otra_mano_buena_no_cuenta_como_escalera_de_color(self):
        mano(1, self.ana, gano=100, hand_name="Full")
        self.assertFalse(self._estado("escalera_de_color")["unlocked"])

    def test_tres_manos_seguidas_desbloquean_la_racha(self):
        for numero in (1, 2, 3):
            mano(numero, self.ana, gano=100)
        self.assertTrue(self._estado("tres_seguidas")["unlocked"])
        self.assertEqual(self._estado("tres_seguidas")["progress"], 3)

    def test_una_derrota_corta_la_racha(self):
        for numero in (1, 2):
            mano(numero, self.ana, gano=100)
        mano(3, self.ana, gano=0)
        mano(4, self.ana, gano=100)
        # Mejor racha del historial: dos, no tres.
        self.assertEqual(mejor_racha(list(self.ana.poker_hands_played.all())), 2)
        self.assertFalse(self._estado("tres_seguidas")["unlocked"])

    def test_las_manos_de_otro_no_cuentan(self):
        luis = User.objects.create_user("luis", "luis@example.com", "Zx9!pqLmn42")
        UserProfile.objects.get_or_create(user=luis)
        mano(1, luis, gano=100, hand_name=ESCALERA_DE_COLOR)
        self.assertFalse(self._estado("primera_mano")["unlocked"])
        self.assertFalse(self._estado("escalera_de_color")["unlocked"])


class LogrosEndpointTests(TestCase):
    def setUp(self):
        self.ana = User.objects.create_user("ana", "ana@example.com", "Zx9!pqLmn42")
        UserProfile.objects.get_or_create(user=self.ana)
        self.client = APIClient()

    def test_sin_sesion_no_se_puede_ver(self):
        self.assertEqual(self.client.get("/api/poker/achievements/").status_code, 401)

    def test_devuelve_los_logros_con_el_recuento(self):
        mano(1, self.ana, gano=100)
        mano(2, self.ana, gano=100, hand_name=ESCALERA_DE_COLOR)
        self.client.force_authenticate(self.ana)
        datos = self.client.get("/api/poker/achievements/").json()

        self.assertEqual(datos["total"], 3)
        self.assertEqual(datos["unlocked"], 2)      # primera mano + escalera de color
        ids = [logro["id"] for logro in datos["achievements"]]
        self.assertEqual(ids, ["primera_mano", "escalera_de_color", "tres_seguidas"])
        for logro in datos["achievements"]:
            self.assertIn("unlocked", logro)
            self.assertIn("progress", logro)
            self.assertIn("target", logro)

    def test_el_logro_de_racha_lleva_su_progreso(self):
        mano(1, self.ana, gano=100)
        mano(2, self.ana, gano=100)
        self.client.force_authenticate(self.ana)
        datos = self.client.get("/api/poker/achievements/").json()
        racha = next(logro for logro in datos["achievements"]
                     if logro["id"] == "tres_seguidas")
        self.assertFalse(racha["unlocked"])
        self.assertEqual(racha["progress"], 2)
        self.assertEqual(racha["target"], 3)
