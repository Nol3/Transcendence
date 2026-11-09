"""Perfil, estadísticas, avatares y autenticación.

Estos dos módulos (`apps/users/views.py` al 54 % y `auth_views.py` al 57 %) tenían sin cubrir
justo las partes delicadas: la validación del avatar que se añadió el 16-10 (antes se guardaba
un `.txt` o un `.html` en el directorio público), el cálculo de rachas y clasificación, la
**rotación del refresh** y el login con Google.

Se prueba lo que hace y lo que **no** debe hacer: subir un no-imagen, pasar de 2 MB, reutilizar
un refresh ya rotado o entrar con un token de Google sin verificar.
"""

import io
import shutil
import tempfile
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.games.models import Game
from apps.users.models import UserProfile


def png(valor: int = 10, lado: int = 8) -> bytes:
    """Un PNG de verdad, en memoria."""
    buffer = io.BytesIO()
    Image.new("RGB", (lado, lado), (valor, valor, valor)).save(buffer, format="PNG")
    return buffer.getvalue()


class BaseUsuarios(TestCase):
    """Ana (1700 de ELO), Luis y un tercero con más ELO que Ana para probar el ranking."""

    def setUp(self):
        cache.clear()  # los límites de login viven en la caché del proceso
        self.ana = User.objects.create_user("ana", "ana@example.com", "Zx9!pqLmn42")
        self.luis = User.objects.create_user("luis", "luis@example.com", "Zx9!pqLmn42")
        self.marta = User.objects.create_user("marta", "marta@example.com", "Zx9!pqLmn42")
        UserProfile.objects.create(user=self.ana, elo_rating=1700, win_count=3, loss_count=1)
        UserProfile.objects.create(user=self.luis, elo_rating=1500)
        UserProfile.objects.create(user=self.marta, elo_rating=1800)

    def como(self, usuario) -> APIClient:
        cliente = APIClient()
        cliente.force_authenticate(usuario)
        return cliente


class AvatarTests(BaseUsuarios):
    def setUp(self):
        super().setUp()
        self.media = tempfile.mkdtemp(prefix="ts-media-")
        self.override = override_settings(MEDIA_ROOT=self.media)
        self.override.enable()
        # El perfil nace con un avatar por defecto, así que «no se guardó» se comprueba
        # comparando con el que había, no con un campo vacío.
        self.avatar_previo = self.ana.profile.avatar.name

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media, ignore_errors=True)

    def _subir(self, contenido: bytes, nombre="a.png", tipo="image/png"):
        return SimpleUploadedFile(nombre, contenido, content_type=tipo)

    def test_un_png_valido_se_guarda(self):
        cliente = self.como(self.ana)
        res = cliente.post(
            "/api/users/me/upload_avatar/",
            {"avatar": self._subir(png())},
            format="multipart",
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("/media/", res.json()["data"]["avatarUrl"])
        self.ana.profile.refresh_from_db()
        self.assertTrue(self.ana.profile.avatar)

    def test_un_fichero_que_no_es_imagen_se_rechaza(self):
        """El content-type lo pone el cliente: se mira el contenido de verdad."""
        cliente = self.como(self.ana)
        res = cliente.post(
            "/api/users/me/upload_avatar/",
            {
                "avatar": self._subir(
                    b"<html><script>alert(1)</script></html>", "x.html", "image/png"
                )
            },
            format="multipart",
            # El mensaje se traduce por `Accept-Language`: así se comprueba la traducción real.
            HTTP_ACCEPT_LANGUAGE="es",
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("imagen", res.json()["error"])
        self.ana.profile.refresh_from_db()
        self.assertEqual(self.ana.profile.avatar.name, self.avatar_previo)

    def test_por_encima_de_dos_megas_se_rechaza(self):
        cliente = self.como(self.ana)
        grande = b"\x89PNG\r\n\x1a\n" + b"0" * (2 * 1024 * 1024 + 10)
        res = cliente.post(
            "/api/users/me/upload_avatar/",
            {"avatar": self._subir(grande)},
            format="multipart",
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("MB", res.json()["error"])

    def test_sin_fichero_avisa(self):
        res = self.como(self.ana).post("/api/users/me/upload_avatar/", {}, format="multipart")
        self.assertEqual(res.status_code, 400)
        self.assertIn("No avatar", res.json()["error"])

    def test_el_perfil_tambien_valida_el_avatar(self):
        res = self.como(self.ana).patch(
            "/api/users/me/update_profile/",
            {"avatar": self._subir(b"no soy una imagen", "nota.txt", "image/png")},
            format="multipart",
            HTTP_ACCEPT_LANGUAGE="es",
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("imagen", res.json()["error"])

    def test_editar_el_perfil_con_avatar_valido(self):
        res = self.como(self.ana).patch(
            "/api/users/me/update_profile/",
            {"username": "ana2", "avatar": self._subir(png(200))},
            format="multipart",
        )
        self.assertEqual(res.status_code, 200)
        self.ana.refresh_from_db()
        self.assertEqual(self.ana.username, "ana2")


class PerfilTests(BaseUsuarios):
    def test_el_nombre_de_usuario_no_puede_pisar_otro(self):
        res = self.como(self.ana).patch(
            "/api/users/me/update_profile/", {"username": "luis"}, format="json"
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("taken", res.json()["error"])

    def test_poner_tu_mismo_nombre_no_es_un_error(self):
        res = self.como(self.ana).patch(
            "/api/users/me/update_profile/", {"username": "ana"}, format="json"
        )
        self.assertEqual(res.status_code, 200)

    def test_me_devuelve_tu_email_pero_el_de_otro_no(self):
        propio = self.como(self.ana).get("/api/users/me/")
        ajeno = self.como(self.ana).get(f"/api/users/{self.luis.id}/")
        self.assertEqual(propio.json()["email"], "ana@example.com")
        self.assertNotIn("email", ajeno.json())

    def test_escribir_la_cuenta_de_otro_da_404(self):
        """El IDOR del 16-10: `PATCH /api/users/<id>/` sobre otra cuenta."""
        cliente = self.como(self.ana)
        self.assertEqual(
            cliente.patch(
                f"/api/users/{self.luis.id}/", {"username": "robado"}, format="json"
            ).status_code,
            404,
        )
        self.assertEqual(cliente.delete(f"/api/users/{self.luis.id}/").status_code, 404)
        self.assertTrue(User.objects.filter(pk=self.luis.pk).exists())

    def test_borrar_la_propia_cuenta(self):
        self.assertEqual(self.como(self.ana).delete(f"/api/users/{self.ana.id}/").status_code, 204)
        self.assertFalse(User.objects.filter(pk=self.ana.pk).exists())


class EstadisticasTests(BaseUsuarios):
    def setUp(self):
        super().setUp()
        hoy = timezone.now()
        orden = [("win", True), ("win", True), ("loss", True), ("win", True)]
        for i, (resultado, puntuable) in enumerate(orden):
            Game.objects.create(
                player1=self.ana,
                player2=self.luis,
                winner=self.ana if resultado == "win" else self.luis,
                status="finished",
                rated=puntuable,
                finished_at=hoy - timedelta(hours=10 - i),
            )
        # Una sin terminar: no cuenta para nada.
        Game.objects.create(player1=self.ana, player2=self.luis, status="pending")

    def test_la_racha_cuenta_solo_victorias_seguidas_y_puntuables(self):
        datos = self.como(self.ana).get("/api/users/me/stats/").json()["data"]
        # Secuencia: gana, gana, pierde, gana -> la racha más larga es 2 y la actual 1.
        self.assertEqual(datos["longestStreak"], 2)
        self.assertEqual(datos["currentStreak"], 1)

    def test_el_balance_y_el_porcentaje_salen_del_perfil(self):
        datos = self.como(self.ana).get("/api/users/me/stats/").json()["data"]
        self.assertEqual((datos["wins"], datos["losses"]), (3, 1))
        self.assertEqual(datos["gamesPlayed"], 4)
        self.assertEqual(datos["winRate"], 75.0)

    def test_la_clasificacion_cuenta_a_quien_tiene_mas_elo(self):
        datos = self.como(self.ana).get("/api/users/me/stats/").json()["data"]
        self.assertEqual(datos["rank"], 2)  # Marta está por encima con 1800

    def test_las_estadisticas_de_otro_y_su_404(self):
        cliente = self.como(self.ana)
        self.assertEqual(
            cliente.get(f"/api/users/{self.luis.id}/stats/").json()["data"]["gamesPlayed"], 0
        )
        self.assertEqual(cliente.get("/api/users/99999/stats/").status_code, 404)

    def test_sin_partidas_el_porcentaje_es_cero(self):
        # Marta no ha jugado ninguna partida (Luis sí: es el rival en las de arriba).
        datos = self.como(self.marta).get("/api/users/me/stats/").json()["data"]
        self.assertEqual((datos["winRate"], datos["longestStreak"]), (0, 0))


class HistorialTests(BaseUsuarios):
    def setUp(self):
        super().setUp()
        base = timezone.now() - timedelta(days=1)
        # Ana como jugadora 1: gana 3-1.
        self.como_p1 = Game.objects.create(
            player1=self.ana,
            player2=self.luis,
            winner=self.ana,
            status="finished",
            player1_score=3,
            player2_score=1,
            finished_at=base,
        )
        # Ana como jugadora 2: pierde 0-2. El marcador se cuenta desde SU lado.
        self.como_p2 = Game.objects.create(
            player1=self.luis,
            player2=self.ana,
            winner=self.luis,
            status="finished",
            player1_score=2,
            player2_score=0,
            finished_at=base + timedelta(hours=1),
        )
        # Empate (sin ganador).
        self.empate = Game.objects.create(
            player1=self.ana,
            player2=self.marta,
            winner=None,
            status="finished",
            player1_score=1,
            player2_score=1,
            finished_at=base + timedelta(hours=2),
        )
        # Sin terminar: fuera del historial.
        Game.objects.create(player1=self.ana, player2=self.luis, status="pending")

    def test_el_historial_trae_resultado_rival_y_marcador_propio(self):
        cuerpo = self.como(self.ana).get("/api/users/me/history/").json()
        self.assertEqual(cuerpo["meta"]["total"], 3)
        por_id = {fila["id"]: fila for fila in cuerpo["data"]}

        p1 = por_id[str(self.como_p1.id)]
        self.assertEqual((p1["result"], p1["score"]), ("win", "3-1"))
        self.assertEqual(p1["opponent"]["username"], "luis")

        p2 = por_id[str(self.como_p2.id)]
        self.assertEqual((p2["result"], p2["score"]), ("loss", "0-2"))

        empate = por_id[str(self.empate.id)]
        self.assertEqual((empate["result"], empate["opponent"]["username"]), ("draw", "marta"))

    def test_el_historial_pagina(self):
        cuerpo = self.como(self.ana).get("/api/users/me/history/?page=2&limit=2").json()
        self.assertEqual(len(cuerpo["data"]), 1)
        self.assertEqual(cuerpo["meta"]["totalPages"], 2)

    def test_el_historial_de_otro_y_su_404(self):
        cliente = self.como(self.ana)
        self.assertEqual(cliente.get(f"/api/users/{self.luis.id}/history/").status_code, 200)
        self.assertEqual(cliente.get("/api/users/99999/history/").status_code, 404)


class LoginTests(BaseUsuarios):
    def test_entrar_con_email_devuelve_tokens_y_usuario(self):
        res = APIClient().post(
            "/api/auth/login/",
            {"email": "ana@example.com", "password": "Zx9!pqLmn42"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        datos = res.json()["data"]
        self.assertEqual(datos["user"]["username"], "ana")
        self.assertTrue(datos["tokens"]["accessToken"])
        self.assertTrue(datos["tokens"]["refreshToken"])

    def test_entrar_con_el_nombre_de_usuario_tambien_vale(self):
        res = APIClient().post(
            "/api/auth/login/", {"email": "ana", "password": "Zx9!pqLmn42"}, format="json"
        )
        self.assertEqual(res.status_code, 200)

    def test_contraseña_mal_da_401_y_no_dice_cual_era(self):
        res = APIClient().post(
            "/api/auth/login/", {"email": "ana@example.com", "password": "otra"}, format="json"
        )
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json()["error"], "Invalid credentials")

    def test_faltan_campos_da_400(self):
        self.assertEqual(APIClient().post("/api/auth/login/", {}, format="json").status_code, 400)

    def test_un_correo_que_no_existe_no_revela_nada(self):
        res = APIClient().post(
            "/api/auth/login/", {"email": "nadie@example.com", "password": "x"}, format="json"
        )
        self.assertEqual(res.status_code, 401)


class RegistroTests(BaseUsuarios):
    def test_registro_crea_usuario_perfil_y_tokens(self):
        res = APIClient().post(
            "/api/auth/register/",
            {"username": "nuevo", "email": "nuevo@example.com", "password": "Zx9!pqLmn42"},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        usuario = User.objects.get(username="nuevo")
        self.assertTrue(UserProfile.objects.filter(user=usuario).exists())
        self.assertTrue(res.json()["data"]["tokens"]["accessToken"])

    def test_un_nombre_repetido_da_400_con_el_detalle(self):
        res = APIClient().post(
            "/api/auth/register/",
            {"username": "ana", "email": "otro@example.com", "password": "Zx9!pqLmn42"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("error", res.json())
        self.assertIn("errors", res.json())

    def test_una_contraseña_debil_no_pasa_los_validadores(self):
        res = APIClient().post(
            "/api/auth/register/",
            {"username": "debil", "email": "debil@example.com", "password": "12345678"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)


class RefrescoYLogoutTests(BaseUsuarios):
    def _tokens(self):
        """Los tokens se crean aquí (sync): `for_user` escribe en la tabla del blacklist."""
        refresh = RefreshToken.for_user(self.ana)
        return str(refresh), str(refresh.access_token)

    def test_el_refresh_rota_y_devuelve_token_nuevo(self):
        refresh, _ = self._tokens()
        res = APIClient().post("/api/auth/refresh/", {"refreshToken": refresh}, format="json")
        self.assertEqual(res.status_code, 200)
        nuevo = res.json()["data"]["tokens"]["refreshToken"]
        self.assertNotEqual(nuevo, refresh)

    def test_el_refresh_usado_ya_no_sirve(self):
        """Rotación de verdad: reutilizar el anterior es 401, no otra sesión."""
        refresh, _ = self._tokens()
        cliente = APIClient()
        self.assertEqual(
            cliente.post(
                "/api/auth/refresh/", {"refreshToken": refresh}, format="json"
            ).status_code,
            200,
        )
        self.assertEqual(
            cliente.post(
                "/api/auth/refresh/", {"refreshToken": refresh}, format="json"
            ).status_code,
            401,
        )

    def test_sin_refresh_da_400_y_con_basura_401(self):
        cliente = APIClient()
        self.assertEqual(cliente.post("/api/auth/refresh/", {}, format="json").status_code, 400)
        self.assertEqual(
            cliente.post(
                "/api/auth/refresh/", {"refreshToken": "basura"}, format="json"
            ).status_code,
            401,
        )

    def test_logout_revoca_el_refresh(self):
        refresh, _ = self._tokens()
        cliente = APIClient()
        self.assertEqual(
            cliente.post("/api/auth/logout/", {"refreshToken": refresh}, format="json").status_code,
            200,
        )
        self.assertEqual(
            cliente.post(
                "/api/auth/refresh/", {"refreshToken": refresh}, format="json"
            ).status_code,
            401,
        )

    def test_logout_sin_token_no_revienta(self):
        """Quien se va sin credencial no tiene que recibir un error."""
        self.assertEqual(APIClient().post("/api/auth/logout/", {}, format="json").status_code, 200)
        self.assertEqual(
            APIClient()
            .post("/api/auth/logout/", {"refreshToken": "basura"}, format="json")
            .status_code,
            200,
        )

    def test_me_exige_sesion(self):
        self.assertEqual(APIClient().get("/api/auth/me/").status_code, 401)
        res = self.como(self.ana).get("/api/auth/me/")
        self.assertEqual(res.json()["data"]["user"]["email"], "ana@example.com")


class GoogleTests(BaseUsuarios):
    URL = "/api/auth/google/"

    def test_sin_credencial_da_400(self):
        self.assertEqual(APIClient().post(self.URL, {}, format="json").status_code, 400)

    @override_settings(GOOGLE_CLIENT_ID="")
    def test_si_no_esta_configurado_avisa_con_503(self):
        res = APIClient().post(self.URL, {"credential": "x"}, format="json")
        self.assertEqual(res.status_code, 503)

    @override_settings(GOOGLE_CLIENT_ID="cliente-de-prueba.apps.googleusercontent.com")
    def test_un_token_que_google_rechaza_da_401(self):
        with patch(
            "apps.users.auth_views.google_id_token.verify_oauth2_token",
            side_effect=ValueError("token caducado"),
        ):
            res = APIClient().post(self.URL, {"credential": "x"}, format="json")
        self.assertEqual(res.status_code, 401)
        self.assertIn("Invalid Google token", res.json()["error"])

    @override_settings(GOOGLE_CLIENT_ID="cliente-de-prueba.apps.googleusercontent.com")
    def test_un_correo_sin_verificar_no_vale(self):
        with patch(
            "apps.users.auth_views.google_id_token.verify_oauth2_token",
            return_value={"email": "nuevo@example.com", "email_verified": False},
        ):
            res = APIClient().post(self.URL, {"credential": "x"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertFalse(User.objects.filter(email="nuevo@example.com").exists())

    @override_settings(GOOGLE_CLIENT_ID="cliente-de-prueba.apps.googleusercontent.com")
    def test_un_usuario_nuevo_se_crea_sin_contraseña_y_con_perfil(self):
        with patch(
            "apps.users.auth_views.google_id_token.verify_oauth2_token",
            return_value={
                "email": "google@example.com",
                "email_verified": True,
                "given_name": "Google",
                "family_name": "Test",
            },
        ):
            res = APIClient().post(self.URL, {"credential": "x"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["data"]["is_new_user"])
        usuario = User.objects.get(email="google@example.com")
        self.assertFalse(usuario.has_usable_password())
        self.assertTrue(UserProfile.objects.filter(user=usuario).exists())
        self.assertEqual(usuario.username, "google")

    @override_settings(GOOGLE_CLIENT_ID="cliente-de-prueba.apps.googleusercontent.com")
    def test_un_usuario_que_ya_existe_entra_sin_crear_otro(self):
        with patch(
            "apps.users.auth_views.google_id_token.verify_oauth2_token",
            return_value={"email": "ana@example.com", "email_verified": True},
        ):
            res = APIClient().post(self.URL, {"credential": "x"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.json()["data"]["is_new_user"])
        self.assertEqual(User.objects.filter(email="ana@example.com").count(), 1)

    @override_settings(GOOGLE_CLIENT_ID="cliente-de-prueba.apps.googleusercontent.com")
    def test_el_nombre_sale_unico_si_ya_esta_cogido(self):
        """Dos «Ana» de Google no pueden acabar con el mismo `username`."""
        with patch(
            "apps.users.auth_views.google_id_token.verify_oauth2_token",
            return_value={"email": "otra@example.com", "email_verified": True, "given_name": "Ana"},
        ):
            res = APIClient().post(self.URL, {"credential": "x"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["data"]["user"]["username"], "ana1")
