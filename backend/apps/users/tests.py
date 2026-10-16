"""Tests de la app de usuarios.

Fijan el hallazgo C1 de `docs/AUDITORIA_PROYECTO.md`: el listado y la ficha de
otros usuarios **no** pueden exponer direcciones de correo. El email solo viaja
al propio interesado.
"""
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from apps.users.models import UserProfile


class UserPrivacyTests(TestCase):
    def setUp(self):
        self.ana = User.objects.create_user("ana", "ana@example.com", "Zx9!pqLmn42")
        self.luis = User.objects.create_user("luis", "luis@example.com", "Zx9!pqLmn42")
        for u in (self.ana, self.luis):
            UserProfile.objects.get_or_create(user=u)
        self.client = APIClient()
        self.client.force_authenticate(self.ana)

    def test_el_listado_de_usuarios_no_expone_emails(self):
        res = self.client.get("/api/users/")
        self.assertEqual(res.status_code, 200)
        filas = res.data["results"] if isinstance(res.data, dict) else res.data
        self.assertTrue(filas, "debería devolver usuarios")
        for fila in filas:
            self.assertNotIn("email", fila, "el listado no debe llevar emails")
        # Comprobación a nivel de texto: ni un correo en toda la respuesta.
        self.assertNotIn("@example.com", str(res.data))

    def test_la_ficha_de_otro_usuario_no_expone_email(self):
        res = self.client.get(f"/api/users/{self.luis.id}/")
        self.assertEqual(res.status_code, 200)
        self.assertNotIn("email", res.data)

    def test_el_propio_usuario_si_ve_su_email(self):
        res = self.client.get("/api/auth/me/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"]["user"]["email"], "ana@example.com")

    def test_el_perfil_propio_sigue_trayendo_el_email(self):
        res = self.client.get("/api/users/me/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["email"], "ana@example.com")

    def test_el_torneo_no_expone_emails(self):
        from apps.tournament.models import Tournament, TournamentParticipant

        t = Tournament.objects.create(name="Copa", creator=self.ana, max_players=4)
        TournamentParticipant.objects.create(tournament=t, user=self.luis)
        res = self.client.get(f"/api/tournament/{t.id}/")
        self.assertEqual(res.status_code, 200)
        self.assertNotIn("@example.com", str(res.data))

    def test_el_chat_no_expone_emails(self):
        """El serializador de mensajes usa el usuario público (sin email)."""
        from apps.chat.models import Message
        from apps.chat.serializers import MessageSerializer

        msg = Message.objects.create(sender=self.ana, recipient=self.luis, content="hola")
        data = MessageSerializer(msg).data
        self.assertNotIn("email", data["sender"])
        self.assertNotIn("email", data["recipient"])
        self.assertEqual(data["sender"]["username"], "ana")
