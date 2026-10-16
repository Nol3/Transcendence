"""Replay de manos (roadmap 7.2): se guarda el registro de acciones y se sirve.

El replay paso a paso solo es posible si la mano se guarda con lo que fue pasando, así
que aquí se comprueban las dos mitades: que el registro llega a la base de datos y que
la API lo devuelve **solo a quien jugó esa mano**.
"""
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from apps.poker.models import PokerHandPlayer, PokerHandRecord
from apps.poker.services import _save_hands

ACCIONES = [
    {"event": "hand_start", "button": 0, "sb": 10, "bb": 20, "stacks": [1000, 1000]},
    {"event": "blind", "seat": 0, "kind": "sb", "amount": 10},
    {"event": "action", "seat": 0, "action": "raise", "amount": 60,
     "committed": 60, "street": "preflop"},
    {"event": "street", "street": "flop", "board": ["7c", "2s", "Ad"]},
    {"event": "hand_end", "winner": 0, "amount": 140, "showdown": False},
]


class _MesaFalsa:
    """Mesa mínima: `_save_hands` solo necesita `id` y la lista de resúmenes."""

    def __init__(self, resumenes):
        self.id = "mesa-replay"
        self.hands = resumenes


class GuardadoDelRegistroTests(TestCase):
    def setUp(self):
        self.ana = User.objects.create_user("ana", "ana@example.com", "Zx9!pqLmn42")

    def _resumen(self, **extra):
        resumen = {
            "hand_number": 1,
            "board": "7c 2s Ad",
            "pot": 140,
            "showdown": False,
            "winner_names": "ana",
            "players": [{
                "seat": 0, "user_id": self.ana.id, "name": "ana", "is_bot": False,
                "hole": "", "hand_name": "", "stack_after": 1080, "won": 140,
                "folded": False,
            }],
        }
        resumen.update(extra)
        return resumen

    def test_guarda_las_acciones_de_la_mano(self):
        _save_hands(None, _MesaFalsa([self._resumen(actions=ACCIONES)]))
        mano = PokerHandRecord.objects.get()
        self.assertEqual(len(mano.actions), 5)
        self.assertEqual(mano.actions[0]["event"], "hand_start")
        self.assertEqual(mano.actions[-1]["event"], "hand_end")

    def test_mano_sin_registro_se_guarda_con_lista_vacia(self):
        # Las manos antiguas no tienen registro; no debe romper nada.
        _save_hands(None, _MesaFalsa([self._resumen()]))
        self.assertEqual(PokerHandRecord.objects.get().actions, [])

    def test_guarda_varias_manos_con_su_registro(self):
        resumenes = [
            self._resumen(hand_number=1, actions=ACCIONES),
            self._resumen(hand_number=2, actions=ACCIONES[:2]),
        ]
        guardadas = _save_hands(None, _MesaFalsa(resumenes))
        self.assertEqual(guardadas, 2)
        self.assertEqual(
            [len(m.actions) for m in PokerHandRecord.objects.order_by("hand_number")],
            [5, 2],
        )


class EndpointDelReplayTests(TestCase):
    def setUp(self):
        self.ana = User.objects.create_user("ana", "ana@example.com", "Zx9!pqLmn42")
        self.luis = User.objects.create_user("luis", "luis@example.com", "Zx9!pqLmn42")
        self.mano = PokerHandRecord.objects.create(
            table_id="mesa-replay", hand_number=3, board="7c 2s Ad", pot=140,
            showdown=False, winner_names="ana", actions=ACCIONES,
        )
        PokerHandPlayer.objects.create(
            hand=self.mano, user=self.ana, seat=0, name="ana", won=140,
        )
        PokerHandPlayer.objects.create(
            hand=self.mano, seat=1, name="Bot Test", is_bot=True,
        )
        self.client = APIClient()

    def _url(self, hand_id=None):
        return f"/api/poker/history/hand/{hand_id or self.mano.id}/"

    def test_devuelve_la_mano_con_sus_acciones(self):
        self.client.force_authenticate(self.ana)
        r = self.client.get(self._url())
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["hand_number"], 3)
        self.assertEqual(len(r.data["actions"]), 5)
        self.assertEqual(r.data["actions"][1]["event"], "blind")
        # Los jugadores siguen viniendo, para pintar la mesa en el replay.
        self.assertEqual(len(r.data["players"]), 2)

    def test_la_mano_de_otro_no_se_ve(self):
        self.client.force_authenticate(self.luis)
        r = self.client.get(self._url())
        self.assertEqual(r.status_code, 403)
        self.assertNotIn("actions", r.data)

    def test_mano_inexistente_da_404(self):
        self.client.force_authenticate(self.ana)
        self.assertEqual(self.client.get(self._url(999999)).status_code, 404)

    def test_sin_sesion_da_401(self):
        self.assertIn(self.client.get(self._url()).status_code, (401, 403))
