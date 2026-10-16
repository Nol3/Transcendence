"""Preferencias del póker online (5.5): tema del tapete, ciegas y tamaño de mesa.

Es lo que lleva al póker online el módulo «game customization», que hasta ahora solo
aplicaba al juego local.
"""
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from apps.poker.consumers import STAKE_LEVELS, TABLE_SIZES
from apps.poker.models import PokerPreference
from apps.users.models import UserProfile


class PokerPreferenceTests(TestCase):
    def setUp(self):
        self.ana = User.objects.create_user("ana", "ana@example.com", "Zx9!pqLmn42")
        self.luis = User.objects.create_user("luis", "luis@example.com", "Zx9!pqLmn42")
        for u in (self.ana, self.luis):
            UserProfile.objects.get_or_create(user=u)
        self.client = APIClient()
        self.client.force_authenticate(self.ana)

    def test_sin_preferencias_devuelve_las_de_por_defecto(self):
        res = self.client.get("/api/poker/preferences/")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["theme"], "classic")
        self.assertEqual(res.data["stake"], "low")
        self.assertEqual(res.data["table_size"], 2)
        self.assertEqual(len(res.data["themes"]), 5)
        self.assertEqual(PokerPreference.objects.filter(user=self.ana).count(), 1)

    def test_se_puede_cambiar_el_tema_y_queda_guardado(self):
        res = self.client.put("/api/poker/preferences/", {"theme": "neon"}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["theme"], "neon")

        # Persistido: una lectura nueva lo devuelve igual.
        self.assertEqual(self.client.get("/api/poker/preferences/").data["theme"], "neon")
        self.assertEqual(PokerPreference.objects.get(user=self.ana).theme, "neon")

    def test_se_pueden_cambiar_ciegas_y_tamano_de_mesa(self):
        res = self.client.put(
            "/api/poker/preferences/",
            {"stake": "mid", "table_size": 6},
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["stake"], "mid")
        self.assertEqual(res.data["table_size"], 6)

    def test_los_valores_invalidos_se_rechazan_y_no_cambian_nada(self):
        self.client.put("/api/poker/preferences/", {"theme": "neon"}, format="json")
        for payload in (
            {"theme": "arcoiris"},
            {"stake": "alto"},
            {"table_size": 9},
            {"table_size": "muchas"},
        ):
            res = self.client.put("/api/poker/preferences/", payload, format="json")
            self.assertEqual(res.status_code, 400, f"{payload} debería dar 400")
            self.assertIn("error", res.data)
        pref = PokerPreference.objects.get(user=self.ana)
        self.assertEqual(pref.theme, "neon", "lo válido anterior sigue en pie")
        self.assertEqual(pref.table_size, 2)

    def test_cada_usuario_tiene_sus_preferencias(self):
        self.client.put("/api/poker/preferences/", {"theme": "gold"}, format="json")
        otro = APIClient()
        otro.force_authenticate(self.luis)
        self.assertEqual(otro.get("/api/poker/preferences/").data["theme"], "classic")
        self.assertEqual(self.client.get("/api/poker/preferences/").data["theme"], "gold")

    def test_sin_sesion_no_hay_preferencias(self):
        anon = APIClient()
        self.assertIn(anon.get("/api/poker/preferences/").status_code, (401, 403))
        self.assertIn(
            anon.put("/api/poker/preferences/", {"theme": "neon"}, format="json").status_code,
            (401, 403),
        )

    def test_los_limites_del_backend_coinciden_con_los_de_la_cola(self):
        """El tamaño guardado tiene que ser uno de los que acepta la cola."""
        self.assertEqual(sorted(TABLE_SIZES), [2, 3, 4, 5, 6])
        self.assertEqual(set(STAKE_LEVELS), {"micro", "low", "mid"})
        for size in TABLE_SIZES:
            res = self.client.put(
                "/api/poker/preferences/", {"table_size": size}, format="json"
            )
            self.assertEqual(res.status_code, 200, f"{size} debería valer")
        for stake in STAKE_LEVELS:
            res = self.client.put("/api/poker/preferences/", {"stake": stake}, format="json")
            self.assertEqual(res.status_code, 200, f"{stake} debería valer")
