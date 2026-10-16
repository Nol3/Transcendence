"""Tests de la app de chat.

Fijan el hallazgo B1 de `docs/AUDITORIA_PROYECTO.md`: los endpoints del chat
devolvían 500 (`models.Q` sin importar `models`) y `send_message` no validaba
nada: aceptaba destinatarios inexistentes, mensajes vacíos y mensajes a uno mismo.
"""
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from apps.chat.models import Message
from apps.users.models import UserProfile


class ChatTests(TestCase):
    def setUp(self):
        self.ana = User.objects.create_user("ana", "ana@example.com", "Zx9!pqLmn42")
        self.luis = User.objects.create_user("luis", "luis@example.com", "Zx9!pqLmn42")
        self.marta = User.objects.create_user("marta", "marta@example.com", "Zx9!pqLmn42")
        for u in (self.ana, self.luis, self.marta):
            UserProfile.objects.get_or_create(user=u)
        self.client = APIClient()
        self.client.force_authenticate(self.ana)

    def _mensaje(self, sender, recipient, content="hola"):
        return Message.objects.create(sender=sender, recipient=recipient, content=content)

    # ── el 500 que motivó el hallazgo ────────────────────────────────────────
    def test_listar_mensajes_no_revienta(self):
        self._mensaje(self.luis, self.ana, "¿jugamos?")
        res = self.client.get("/api/chat/messages/")
        self.assertEqual(res.status_code, 200, res.data)

    def test_la_conversacion_no_revienta(self):
        self._mensaje(self.luis, self.ana, "¿jugamos?")
        res = self.client.get(f"/api/chat/messages/conversation/?user_id={self.luis.id}")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(len(res.data), 1)

    def test_solo_veo_los_mensajes_en_los_que_participo(self):
        self._mensaje(self.luis, self.ana, "para ana")
        self._mensaje(self.luis, self.marta, "para marta, no para ana")
        res = self.client.get("/api/chat/messages/")
        self.assertEqual(res.status_code, 200)
        filas = res.data["results"] if isinstance(res.data, dict) else res.data
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]["content"], "para ana")

    # ── validación de la entrada ─────────────────────────────────────────────
    def test_enviar_mensaje_funciona(self):
        res = self.client.post(
            "/api/chat/messages/send_message/",
            {"recipient_id": self.luis.id, "content": "nos vemos en la mesa"},
            format="json",
        )
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(Message.objects.count(), 1)
        msg = Message.objects.get()
        self.assertEqual(msg.sender, self.ana)
        self.assertEqual(msg.recipient, self.luis)

    def test_destinatario_inexistente_da_400_no_500(self):
        res = self.client.post(
            "/api/chat/messages/send_message/",
            {"recipient_id": 99999, "content": "hola"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Message.objects.count(), 0)

    def test_mensaje_vacio_da_400(self):
        res = self.client.post(
            "/api/chat/messages/send_message/",
            {"recipient_id": self.luis.id, "content": "   "},
            format="json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Message.objects.count(), 0)

    def test_no_puedo_enviarme_mensajes_a_mi_mismo(self):
        res = self.client.post(
            "/api/chat/messages/send_message/",
            {"recipient_id": self.ana.id, "content": "hola yo"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Message.objects.count(), 0)

    def test_la_conversacion_sin_user_id_da_400(self):
        res = self.client.get("/api/chat/messages/conversation/")
        self.assertEqual(res.status_code, 400)

    def test_la_conversacion_con_user_id_no_numerico_da_400(self):
        res = self.client.get("/api/chat/messages/conversation/?user_id=abc")
        self.assertEqual(res.status_code, 400)

    # ── privacidad ───────────────────────────────────────────────────────────
    def test_los_mensajes_no_exponen_emails(self):
        self._mensaje(self.luis, self.ana, "hola")
        res = self.client.get("/api/chat/messages/")
        self.assertNotIn("@example.com", str(res.data))

    # ── leído / no leído ─────────────────────────────────────────────────────
    def test_marcar_como_leidos(self):
        self._mensaje(self.luis, self.ana, "uno")
        self._mensaje(self.luis, self.ana, "dos")
        res = self.client.post(
            "/api/chat/messages/mark_read/", {"user_id": self.luis.id}, format="json"
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["marked_read"], 2)
        self.assertFalse(Message.objects.filter(is_read=False).exists())

    # ── autenticación ────────────────────────────────────────────────────────
    def test_sin_sesion_no_se_puede_leer_ni_enviar(self):
        anon = APIClient()
        self.assertIn(anon.get("/api/chat/messages/").status_code, (401, 403))
        self.assertIn(
            anon.post(
                "/api/chat/messages/send_message/",
                {"recipient_id": self.luis.id, "content": "hola"},
                format="json",
            ).status_code,
            (401, 403),
        )
