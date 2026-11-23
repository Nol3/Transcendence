"""Tests de la racha de login (`POST /api/users/me/checkin/`).

La racha es de días de visita, no de victorias: se calcula con la fecha del
servidor y es idempotente dentro del mismo día.
"""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.users.models import UserProfile


class CheckinTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ana", "ana@example.com", "Zx9!pqLmn42")
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_la_primera_visita_empieza_en_uno(self):
        res = self.client.post("/api/users/me/checkin/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"]["streak"], 1)
        self.assertFalse(res.data["data"]["already"])

    def test_el_mismo_dia_no_sube_la_racha(self):
        self.client.post("/api/users/me/checkin/")
        res = self.client.post("/api/users/me/checkin/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"]["streak"], 1)
        self.assertTrue(res.data["data"]["already"])

    def test_el_dia_siguiente_suma_y_actualiza_el_mejor(self):
        self.profile.last_checkin = timezone.localdate() - timedelta(days=1)
        self.profile.login_streak = 2
        self.profile.best_login_streak = 2
        self.profile.save(update_fields=["last_checkin", "login_streak", "best_login_streak"])

        res = self.client.post("/api/users/me/checkin/")
        self.assertEqual(res.data["data"]["streak"], 3)
        self.assertEqual(res.data["data"]["best"], 3)

    def test_un_hueco_de_dos_dias_reinicia(self):
        self.profile.last_checkin = timezone.localdate() - timedelta(days=2)
        self.profile.login_streak = 9
        self.profile.best_login_streak = 9
        self.profile.save(update_fields=["last_checkin", "login_streak", "best_login_streak"])

        res = self.client.post("/api/users/me/checkin/")
        self.assertEqual(res.data["data"]["streak"], 1)
        self.assertEqual(res.data["data"]["best"], 9, "el mejor histórico no se pierde")

    def test_sin_sesion_no_se_puede_fichar(self):
        res = APIClient().post("/api/users/me/checkin/")
        self.assertIn(res.status_code, (401, 403))
