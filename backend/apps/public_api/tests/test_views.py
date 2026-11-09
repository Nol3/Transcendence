"""Tests de la API pública: autenticación por clave, permisos por recurso y paginación.

Este era el módulo con menos cobertura del backend (43 %) y el que recibió el arreglo de
permisos del 16-10-2026: cualquier usuario con sesión podía crearse una clave y editar o
borrar partidas y torneos **ajenos**. Aquí queda fijado ese comportamiento, para que no
vuelva sin que un test se ponga rojo.

La caché se vacía en cada test: los límites de la API (100/h y 20/min) viven en la caché
global del proceso y, sin esto, un test dejaba a 429 al siguiente.
"""
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.games.models import Game
from apps.tournament.models import Tournament
from apps.users.models import UserProfile

from ..models import ApiKey


class BaseApiPublica(TestCase):
    """Dos usuarios con perfil, una clave de API para cada uno y clientes listos."""

    def setUp(self):
        cache.clear()
        self.ana = User.objects.create_user("ana", "ana@example.com", "clave-de-prueba")
        self.luis = User.objects.create_user("luis", "luis@example.com", "clave-de-prueba")
        # Sin perfil a propósito: no debe aparecer en el listado ni en la clasificación, y sirve
        # de «otro» para las partidas que no son de Ana.
        self.pedro = User.objects.create_user("pedro", "pedro@example.com", "clave-de-prueba")
        self.perfil_ana = UserProfile.objects.create(user=self.ana, elo_rating=1700, win_count=3,
                                                     loss_count=1)
        self.perfil_luis = UserProfile.objects.create(user=self.luis, elo_rating=1500)

        self.clave_ana = ApiKey.create_for_user(self.ana, "la de ana")
        self.clave_luis = ApiKey.create_for_user(self.luis, "la de luis")

    # ── Utilidades ──────────────────────────────────────────────────────────

    def api(self, clave=None):
        """Cliente con la cabecera X-API-Key de la clave indicada (por defecto, la de Ana)."""
        cliente = APIClient()
        cliente.credentials(HTTP_X_API_KEY=(clave or self.clave_ana).plain_key)
        return cliente

    def jwt(self, usuario=None):
        """Cliente autenticado con JWT (para gestionar claves)."""
        cliente = APIClient()
        token = RefreshToken.for_user(usuario or self.ana).access_token
        cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return cliente

    @staticmethod
    def partida(p1=None, p2=None, **extra):
        return Game.objects.create(player1=p1, player2=p2, **extra)


class DocumentacionTests(BaseApiPublica):
    def test_la_documentacion_es_publica(self):
        res = self.client.get(reverse("public_api:docs"))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["authentication"]["header"], "X-API-Key")


class AutenticacionTests(BaseApiPublica):
    def test_sin_clave_no_se_pasa(self):
        res = self.client.get(reverse("public_api:user-list"))
        self.assertEqual(res.status_code, 401)

    def test_clave_inventada_no_se_pasa(self):
        cliente = APIClient()
        cliente.credentials(HTTP_X_API_KEY="esto-no-es-una-clave")
        self.assertEqual(cliente.get(reverse("public_api:user-list")).status_code, 401)

    def test_clave_revocada_no_se_pasa(self):
        """Una clave desactivada deja de valer al instante (no hay caché de autenticación)."""
        ApiKey.objects.filter(pk=self.clave_ana.pk).update(is_active=False)
        self.assertEqual(self.api().get(reverse("public_api:user-list")).status_code, 401)

    def test_la_clave_se_guarda_hasheada_y_marca_el_uso(self):
        crudo = self.clave_ana.plain_key
        guardada = ApiKey.objects.get(pk=self.clave_ana.pk)
        self.assertNotEqual(guardada.key, crudo)
        self.assertEqual(len(guardada.key), 64)  # SHA-256 en hexadecimal
        self.assertIsNone(guardada.last_used_at)

        res = self.api().get(reverse("public_api:user-list"))
        self.assertEqual(res.status_code, 200)
        guardada.refresh_from_db()
        self.assertIsNotNone(guardada.last_used_at)


class GestionDeClavesTests(BaseApiPublica):
    def test_crear_clave_devuelve_el_texto_en_claro_una_sola_vez(self):
        res = self.jwt().post(reverse("public_api:key-list-create"), {"name": "para scripts"},
                              format="json")
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.json()["data"]["key"])

        listado = self.jwt().get(reverse("public_api:key-list-create")).json()["data"]
        nueva = next(k for k in listado if k["name"] == "para scripts")
        self.assertNotIn("key", nueva)
        self.assertTrue(nueva["masked_key"].startswith("••••"))

    def test_el_listado_solo_trae_las_claves_propias(self):
        nombres = [k["name"] for k in
                   self.jwt(self.luis).get(reverse("public_api:key-list-create")).json()["data"]]
        self.assertEqual(nombres, ["la de luis"])

    def test_no_se_puede_borrar_la_clave_de_otro(self):
        url = reverse("public_api:key-detail", args=[self.clave_ana.pk])
        self.assertEqual(self.jwt(self.luis).delete(url).status_code, 404)
        self.assertTrue(ApiKey.objects.filter(pk=self.clave_ana.pk).exists())

    def test_la_clave_propia_se_borra(self):
        url = reverse("public_api:key-detail", args=[self.clave_ana.pk])
        self.assertEqual(self.jwt().delete(url).status_code, 204)
        self.assertFalse(ApiKey.objects.filter(pk=self.clave_ana.pk).exists())

    def test_crear_clave_exige_nombre(self):
        res = self.jwt().post(reverse("public_api:key-list-create"), {}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_gestionar_claves_exige_jwt(self):
        cliente = APIClient()
        cliente.credentials(HTTP_X_API_KEY=self.clave_ana.plain_key)
        self.assertEqual(cliente.get(reverse("public_api:key-list-create")).status_code, 401)


class UsuariosTests(BaseApiPublica):
    def test_el_listado_no_lleva_emails(self):
        """Regresión del 12-10: el email de todo el mundo se filtraba por la API."""
        texto = self.api().get(reverse("public_api:user-list")).content.decode()
        self.assertNotIn("ana@example.com", texto)
        self.assertNotIn("email", texto)

    def test_solo_aparecen_los_usuarios_con_perfil(self):
        User.objects.create_user("sinperfil", "sinperfil@example.com", "clave-de-prueba")
        cuerpos = self.api().get(reverse("public_api:user-list")).json()["data"]
        self.assertEqual(sorted(u["username"] for u in cuerpos), ["ana", "luis"])

    def test_detalle_y_404(self):
        self.assertEqual(
            self.api().get(reverse("public_api:user-detail", args=[self.ana.pk])).status_code, 200
        )
        self.assertEqual(
            self.api().get(reverse("public_api:user-detail", args=[99999])).status_code, 404
        )


class PaginacionTests(BaseApiPublica):
    def test_el_limite_se_corta_en_100(self):
        meta = self.api().get(reverse("public_api:user-list"), {"limit": 5000}).json()["meta"]
        self.assertEqual(meta["limit"], 100)

    def test_la_pagina_se_respeta(self):
        meta = self.api().get(reverse("public_api:user-list"), {"page": 2, "limit": 1}).json()["meta"]
        self.assertEqual((meta["page"], meta["total"], meta["total_pages"]), (2, 2, 2))

    def test_una_pagina_que_no_es_un_numero_da_400_y_no_500(self):
        """`?page=abc` reventaba con un ValueError sin capturar (500 en una API pública)."""
        for parametro in ("page", "limit"):
            with self.subTest(parametro=parametro):
                res = self.api().get(reverse("public_api:user-list"), {parametro: "abc"})
                self.assertEqual(res.status_code, 400)


class PartidasTests(BaseApiPublica):
    def setUp(self):
        super().setUp()
        self.mia = self.partida(self.ana, self.luis, status="finished", player1_score=3,
                                player2_score=1, winner=self.ana)
        self.ajena = self.partida(self.luis, self.pedro, status="pending")

    def test_listar_y_filtrar_por_estado(self):
        cuerpos = self.api().get(reverse("public_api:game-list"),
                                 {"status": "finished"}).json()["data"]
        self.assertEqual([g["id"] for g in cuerpos], [self.mia.id])

    def test_crear_partida(self):
        res = self.api().post(reverse("public_api:game-list"),
                              {"player1": self.luis.id, "player2": self.ana.id}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(Game.objects.count(), 3)

    def test_una_partida_no_puede_ser_contra_uno_mismo(self):
        res = self.api().post(reverse("public_api:game-list"),
                              {"player1": self.ana.id, "player2": self.ana.id}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_puedo_editar_y_borrar_lo_mio(self):
        url = reverse("public_api:game-detail", args=[self.mia.pk])
        res = self.api().patch(url, {"player1_score": 7}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(Game.objects.get(pk=self.mia.pk).player1_score, 7)
        self.assertEqual(self.api().delete(url).status_code, 204)
        self.assertFalse(Game.objects.filter(pk=self.mia.pk).exists())

    def test_no_puedo_tocar_lo_ajeno(self):
        """Regresión del 16-10: con una clave cualquiera se editaban partidas de otros."""
        url = reverse("public_api:game-detail", args=[self.ajena.pk])
        cliente = self.api()
        self.assertEqual(cliente.patch(url, {"player1_score": 99}, format="json").status_code, 403)
        self.assertEqual(cliente.delete(url).status_code, 403)
        self.assertEqual(Game.objects.get(pk=self.ajena.pk).player1_score, 0)

    def test_put_completo_tambien_respeta_el_permiso(self):
        url = reverse("public_api:game-detail", args=[self.ajena.pk])
        cuerpo = {"player1": self.luis.id, "player2": self.ana.id, "player1_score": 99}
        self.assertEqual(self.api().put(url, cuerpo, format="json").status_code, 403)

    def test_404_en_partida_que_no_existe(self):
        url = reverse("public_api:game-detail", args=[99999])
        self.assertEqual(self.api().get(url).status_code, 404)
        self.assertEqual(self.api().delete(url).status_code, 404)


class TorneosTests(BaseApiPublica):
    def setUp(self):
        super().setUp()
        self.mio = Tournament.objects.create(name="Mío", creator=self.ana, max_players=8)
        self.ajeno = Tournament.objects.create(name="Ajeno", creator=self.luis, max_players=8)

    def test_crear_torneo_pone_al_creador(self):
        res = self.api().post(reverse("public_api:tournament-list"),
                              {"name": "Nuevo", "max_players": 4}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(Tournament.objects.get(name="Nuevo").creator, self.ana)

    def test_puedo_editar_y_borrar_el_mio(self):
        url = reverse("public_api:tournament-detail", args=[self.mio.pk])
        self.assertEqual(self.api().patch(url, {"name": "Renombrado"}, format="json").status_code, 200)
        self.assertEqual(self.api().delete(url).status_code, 204)

    def test_no_puedo_tocar_el_ajeno(self):
        """Regresión del 16-10: borrar un torneo ajeno se llevaba por delante su bracket."""
        url = reverse("public_api:tournament-detail", args=[self.ajeno.pk])
        self.assertEqual(self.api().patch(url, {"name": "x"}, format="json").status_code, 403)
        self.assertEqual(self.api().delete(url).status_code, 403)
        self.assertTrue(Tournament.objects.filter(pk=self.ajeno.pk).exists())

    def test_listar_y_filtrar_por_estado(self):
        Tournament.objects.filter(pk=self.ajeno.pk).update(status="in_progress")
        cuerpos = self.api().get(reverse("public_api:tournament-list"),
                                 {"status": "in_progress"}).json()["data"]
        self.assertEqual([t["id"] for t in cuerpos], [self.ajeno.id])


class ClasificacionTests(BaseApiPublica):
    def test_ordena_por_elo_y_calcula_el_porcentaje(self):
        cuerpos = self.api().get(reverse("public_api:leaderboard")).json()["data"]
        self.assertEqual([e["username"] for e in cuerpos], ["ana", "luis"])
        primero = cuerpos[0]
        self.assertEqual(primero["rank"], 1)
        self.assertEqual(primero["elo_rating"], 1700)
        self.assertEqual(primero["win_rate"], 75.0)  # 3 victorias de 4

    def test_sin_partidas_el_porcentaje_es_cero(self):
        cuerpos = self.api().get(reverse("public_api:leaderboard")).json()["data"]
        self.assertEqual([e for e in cuerpos if e["username"] == "luis"][0]["win_rate"], 0)

    def test_paginacion_de_la_clasificacion(self):
        meta = self.api().get(reverse("public_api:leaderboard"),
                              {"limit": 1, "page": 2}).json()["meta"]
        self.assertEqual((meta["page"], meta["total"], meta["total_pages"]), (2, 2, 2))
