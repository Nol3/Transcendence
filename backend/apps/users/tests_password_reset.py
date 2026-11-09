"""Recuperar la contraseña: pedir el enlace, canjearlo una vez y cerrar las sesiones.

Lo que se fija aquí, además del camino feliz:

- pedir el enlace **no** revela si el correo existe (misma respuesta y ni un correo de más);
- el enlace caduca y no sirve dos veces (cambiar la contraseña lo invalida solo);
- un token o un `uid` manipulados dan 400, no 500;
- al cambiar la contraseña se caen **todas** las sesiones abiertas, incluido un refresh robado;
- el endpoint tiene límite propio, para que no sirva de ametralladora de correos.
"""
import re

from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import UserProfile

PEDIR = "/api/auth/password-reset/"
CANJEAR = "/api/auth/password-reset/confirm/"
CONTRASEÑA = "Zx9!pqLmn42"
NUEVA = "Nueva-Clave-2026!"


class BaseReset(TestCase):
    def setUp(self):
        cache.clear()  # el límite de peticiones vive en la caché del proceso
        self.ana = User.objects.create_user("ana", "ana@example.com", CONTRASEÑA)
        UserProfile.objects.get_or_create(user=self.ana)
        self.cliente = APIClient()
        mail.outbox.clear()

    def pedir(self, email="ana@example.com"):
        return self.cliente.post(PEDIR, {"email": email}, format="json")

    def enlace_del_correo(self) -> tuple[str, str]:
        """Saca `uid` y `token` del cuerpo del correo, como haría el usuario al pulsarlo."""
        cuerpo = mail.outbox[0].body
        encontrado = re.search(r"reset-password\?uid=([^&\s]+)&token=([^\s]+)", cuerpo)
        self.assertIsNotNone(encontrado, "el correo no trae el enlace")
        return encontrado.group(1), encontrado.group(2)

    def canjear(self, uid, token, password=NUEVA):
        return self.cliente.post(
            CANJEAR, {"uid": uid, "token": token, "password": password}, format="json"
        )


class PedirEnlaceTests(BaseReset):
    def test_manda_el_correo_con_el_enlace(self):
        res = self.pedir()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["ana@example.com"])
        self.assertIn("/reset-password?uid=", mail.outbox[0].body)

    def test_un_correo_que_no_existe_recibe_la_misma_respuesta_y_no_manda_nada(self):
        con_cuenta = self.pedir().json()
        sin_cuenta = self.pedir("nadie@example.com").json()
        self.assertEqual(con_cuenta, sin_cuenta)
        self.assertEqual(len(mail.outbox), 1)  # solo el de Ana

    def test_sin_email_da_400(self):
        self.assertEqual(self.cliente.post(PEDIR, {}, format="json").status_code, 400)

    def test_el_limite_frena_las_peticiones(self):
        for _ in range(5):
            self.assertEqual(self.pedir().status_code, 200)
        self.assertEqual(self.pedir().status_code, 429)


class CanjearEnlaceTests(BaseReset):
    def test_cambia_la_contraseña_y_deja_entrar_con_la_nueva(self):
        self.pedir()
        uid, token = self.enlace_del_correo()
        self.assertEqual(self.canjear(uid, token).status_code, 200)

        self.ana.refresh_from_db()
        self.assertTrue(self.ana.check_password(NUEVA))
        self.assertFalse(self.ana.check_password(CONTRASEÑA))

        login = self.cliente.post(
            "/api/auth/login/", {"email": "ana@example.com", "password": NUEVA}, format="json"
        )
        self.assertEqual(login.status_code, 200)

    def test_el_enlace_no_sirve_dos_veces(self):
        self.pedir()
        uid, token = self.enlace_del_correo()
        self.assertEqual(self.canjear(uid, token).status_code, 200)
        self.assertEqual(self.canjear(uid, token, "Otra-Clave-2026!").status_code, 400)

    def test_un_token_inventado_da_400(self):
        self.pedir()
        uid, _ = self.enlace_del_correo()
        self.assertEqual(self.canjear(uid, "inventado").status_code, 400)

    def test_un_uid_manipulado_da_400_y_no_500(self):
        self.pedir()
        _, token = self.enlace_del_correo()
        for basura in ("no-es-base64!", "", "99999"):
            with self.subTest(uid=basura):
                self.assertEqual(self.canjear(basura, token).status_code, 400)

    def test_una_contraseña_debil_no_pasa(self):
        self.pedir()
        uid, token = self.enlace_del_correo()
        self.assertEqual(self.canjear(uid, token, "12345678").status_code, 400)
        self.ana.refresh_from_db()
        self.assertTrue(self.ana.check_password(CONTRASEÑA))

    def test_sin_contraseña_da_400(self):
        self.pedir()
        uid, token = self.enlace_del_correo()
        self.assertEqual(self.canjear(uid, token, "").status_code, 400)

    @override_settings(PASSWORD_RESET_TIMEOUT=-1)
    def test_el_enlace_caduca(self):
        self.pedir()
        uid, token = self.enlace_del_correo()
        self.assertEqual(self.canjear(uid, token).status_code, 400)

    def test_cambiar_la_contraseña_cierra_las_sesiones_abiertas(self):
        """Un refresh vivo antes del cambio deja de valer: es lo que se espera de un reset."""
        refresh = str(RefreshToken.for_user(self.ana))
        self.pedir()
        uid, token = self.enlace_del_correo()
        self.assertEqual(self.canjear(uid, token).status_code, 200)

        res = self.cliente.post("/api/auth/refresh/", {"refreshToken": refresh}, format="json")
        self.assertEqual(res.status_code, 401)
