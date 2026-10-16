"""Tests de los agujeros que encontró la auditoría del 16-10-2026.

Cada uno fija un fallo que **estaba abierto y verificado** (con peticiones reales, no leyendo
código): cualquiera con sesión podía editar o borrar cuentas ajenas, fabricarse ELO, borrar
torneos y partidas de otros, subir cualquier fichero como avatar o dejar a alguien sin poder
entrar registrando su email.

Van juntos y en un sitio propio a propósito: si alguien vuelve a abrir un `ModelViewSet` sin
`get_queryset`, estos tests lo dicen por su nombre.
"""
from io import BytesIO

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import RequestFactory, TestCase
from rest_framework.test import APIClient
from rest_framework.throttling import AnonRateThrottle

from apps.games.models import Game
from apps.tournament.models import Tournament
from apps.users.models import UserProfile


class _SinLimites(TestCase):
    """Base para los tests que entran por el login: limpian el limitador antes.

    El limitador vive en la caché (en memoria) y es **global al proceso**, así que sin esto
    las peticiones de un test cuentan para el siguiente y el login acaba devolviendo 429 en
    mitad de la suite (o, peor, un test pasando por el motivo equivocado).
    """

    def setUp(self):
        cache.clear()


def crear(nombre: str) -> User:
    user = User.objects.create_user(nombre, f"{nombre}@example.com", "Zx9!pqLmn42")
    UserProfile.objects.get_or_create(user=user)
    return user


class CuentasAjenasTests(TestCase):
    """`/api/users/<id>/` era un IDOR: se podía editar y borrar la cuenta de cualquiera."""

    def setUp(self):
        self.ana = crear("ana")
        self.luis = crear("luis")
        self.client = APIClient()
        self.client.force_authenticate(self.ana)

    def test_no_se_puede_cambiar_el_email_de_otro(self):
        res = self.client.patch(
            f"/api/users/{self.luis.id}/", {"email": "hacked@evil.com"}, format="json"
        )
        self.assertEqual(res.status_code, 404)
        self.luis.refresh_from_db()
        self.assertEqual(self.luis.email, "luis@example.com")

    def test_no_se_puede_borrar_la_cuenta_de_otro(self):
        res = self.client.delete(f"/api/users/{self.luis.id}/")
        self.assertEqual(res.status_code, 404)
        self.assertTrue(User.objects.filter(pk=self.luis.pk).exists())

    def test_la_ficha_publica_si_se_puede_leer_y_no_lleva_email(self):
        res = self.client.get(f"/api/users/{self.luis.id}/")
        self.assertEqual(res.status_code, 200)
        self.assertNotIn("email", res.data)


class EloFabricadoTests(TestCase):
    """`PATCH /api/games/<id>/ {"rated": true}` reabría el agujero A1."""

    def setUp(self):
        self.ana = crear("ana")
        self.luis = crear("luis")
        self.client = APIClient()
        self.client.force_authenticate(self.ana)
        self.game = Game.objects.create(
            player1=self.ana, player2=self.luis, status="in_progress"
        )

    def test_el_rated_no_es_escribible(self):
        # Se parte del valor contrario al que se intenta poner, así el test vale igual si el
        # modelo cambia su valor por defecto.
        self.game.rated = False
        self.game.save(update_fields=["rated"])
        res = self.client.patch(
            f"/api/games/{self.game.id}/", {"rated": True}, format="json"
        )
        # Puede ser 200 (el campo se ignora) o 404 (no es suya), pero nunca cambiar el valor.
        self.game.refresh_from_db()
        self.assertFalse(self.game.rated)
        self.assertIn(res.status_code, (200, 404))

    def test_una_partida_ajena_no_se_ve_ni_se_toca(self):
        intruso = crear("intruso")
        otro = APIClient()
        otro.force_authenticate(intruso)
        self.assertEqual(otro.get(f"/api/games/{self.game.id}/").status_code, 404)
        self.assertEqual(otro.delete(f"/api/games/{self.game.id}/").status_code, 404)

    def test_el_status_no_es_escribible(self):
        self.client.patch(
            f"/api/games/{self.game.id}/", {"status": "finished"}, format="json"
        )
        self.game.refresh_from_db()
        self.assertEqual(self.game.status, "in_progress")


class TorneosAjenosTests(TestCase):
    """`/api/tournament/<id>/` dejaba modificar y borrar torneos de otros."""

    def setUp(self):
        self.ana = crear("ana")
        self.luis = crear("luis")
        self.torneo = Tournament.objects.create(
            name="El de Luis", creator=self.luis, max_players=4
        )
        self.client = APIClient()
        self.client.force_authenticate(self.ana)

    def test_no_se_puede_borrar_el_torneo_de_otro(self):
        res = self.client.delete(f"/api/tournament/{self.torneo.id}/")
        self.assertEqual(res.status_code, 404)
        self.assertTrue(Tournament.objects.filter(pk=self.torneo.pk).exists())

    def test_no_se_puede_renombrar_el_torneo_de_otro(self):
        res = self.client.patch(
            f"/api/tournament/{self.torneo.id}/", {"name": "Mío ahora"}, format="json"
        )
        self.assertEqual(res.status_code, 404)
        self.torneo.refresh_from_db()
        self.assertEqual(self.torneo.name, "El de Luis")


class ApiPublicaTests(TestCase):
    """La API pública con API key borraba recursos de cualquiera."""

    def setUp(self):
        self.ana = crear("ana")
        self.luis = crear("luis")
        self.torneo = Tournament.objects.create(
            name="El de Luis", creator=self.luis, max_players=4
        )
        self.client = APIClient()
        self.client.force_authenticate(self.ana)

    def test_la_api_publica_no_borra_el_torneo_de_otro(self):
        res = self.client.delete(f"/api/public/tournaments/{self.torneo.id}/")
        self.assertEqual(res.status_code, 403)
        self.assertTrue(Tournament.objects.filter(pk=self.torneo.pk).exists())


class AvatarTests(TestCase):
    """El avatar aceptaba cualquier fichero, de cualquier tamaño."""

    def setUp(self):
        self.ana = crear("ana")
        self.client = APIClient()
        self.client.force_authenticate(self.ana)

    def _subir(self, nombre, contenido):
        fichero = BytesIO(contenido)
        fichero.name = nombre
        return self.client.post(
            "/api/users/me/upload_avatar/", {"avatar": fichero}, format="multipart"
        )

    def test_un_texto_no_vale_como_avatar(self):
        res = self._subir("malicioso.txt", b"esto no es una imagen")
        self.assertEqual(res.status_code, 400)

    def test_un_fichero_demasiado_grande_no_vale(self):
        res = self._subir("grande.png", b"\x89PNG\r\n\x1a\n" + b"0" * (3 * 1024 * 1024))
        self.assertEqual(res.status_code, 400)

    def test_una_imagen_de_verdad_si_vale(self):
        # Un PNG 1x1 de verdad (el más pequeño posible).
        png = bytes.fromhex(
            "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
            "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
        )
        res = self._subir("avatar.png", png)
        self.assertEqual(res.status_code, 200)


class LoginEmailDuplicadoTests(_SinLimites):
    """Un email duplicado dejaba a la víctima sin poder entrar (500 para siempre)."""

    def test_el_login_no_revienta_con_dos_cuentas_con_el_mismo_email(self):
        cache.clear()
        User.objects.create_user("victima", "repetido@example.com", "Zx9!pqLmn42")
        User.objects.create_user("otro", "repetido@example.com", "Zx9!pqLmn42")
        res = APIClient().post(
            "/api/auth/login/",
            {"email": "repetido@example.com", "password": "Zx9!pqLmn42"},
            format="json",
        )
        self.assertNotEqual(res.status_code, 500)
        self.assertIn(res.status_code, (200, 401))


class RevocacionJwtTests(_SinLimites):
    """El refresh no se podía revocar: ni rotaba al refrescar ni el logout hacía nada.

    `BLACKLIST_AFTER_ROTATION` estaba en los ajustes, pero sin la app `token_blacklist`
    SimpleJWT lo ignora en silencio, y la vista de refresh era propia y devolvía el mismo
    token de siempre. Un refresh robado valía siete días y no había forma de cortarlo.
    """

    def setUp(self):
        self.ana = crear("ana")
        res = APIClient().post(
            "/api/auth/login/",
            {"email": "ana@example.com", "password": "Zx9!pqLmn42"},
            format="json",
        )
        self.tokens = res.data["data"]["tokens"]

    def _refrescar(self, token):
        return APIClient().post(
            "/api/auth/refresh/", {"refreshToken": token}, format="json"
        )

    def test_el_refresh_rota_y_el_viejo_deja_de_valer(self):
        primera = self._refrescar(self.tokens["refreshToken"])
        self.assertEqual(primera.status_code, 200)
        nuevo = primera.data["data"]["tokens"]["refreshToken"]
        self.assertNotEqual(nuevo, self.tokens["refreshToken"], "tiene que ser otro token")

        # El viejo queda revocado en cuanto se usa...
        self.assertEqual(self._refrescar(self.tokens["refreshToken"]).status_code, 401)
        # ...y el nuevo sigue sirviendo.
        self.assertEqual(self._refrescar(nuevo).status_code, 200)

    def test_el_logout_revoca_el_refresh(self):
        res = APIClient().post(
            "/api/auth/logout/",
            {"refreshToken": self.tokens["refreshToken"]},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self._refrescar(self.tokens["refreshToken"]).status_code, 401)

    def test_un_refresh_inventado_no_revoca_nada_ni_revienta(self):
        res = APIClient().post(
            "/api/auth/logout/", {"refreshToken": "esto.no.es.un.token"}, format="json"
        )
        self.assertEqual(res.status_code, 200)


class LimitadorTests(_SinLimites):
    """El limitador contaba a **todos** los anónimos como uno solo y el login no tenía límite.

    Detrás de nginx, `REMOTE_ADDR` es siempre la IP de nginx: sin `NUM_PROXIES`, DRF metía a
    todo el mundo en el mismo cubo de 60/hora (bastaba con que uno lo agotara para dejar fuera
    a los demás). Con `NUM_PROXIES=1` coge la última entrada de `X-Forwarded-For`, que es la que
    nginx **añade** al final con la IP real: un `X-Forwarded-For` inventado por el cliente no
    sirve para falsear la identidad.
    """

    def _peticion_con(self, xff: str):
        peticion = RequestFactory().get("/", REMOTE_ADDR="172.18.0.5")  # la IP de nginx
        peticion.META["HTTP_X_FORWARDED_FOR"] = xff
        return peticion

    def test_la_ip_es_la_del_cliente_y_no_la_de_nginx(self):
        self.assertEqual(AnonRateThrottle().get_ident(self._peticion_con("1.2.3.4")), "1.2.3.4")

    def test_un_x_forwarded_for_inventado_no_cuenta(self):
        # El cliente manda su propio XFF y nginx añade el real detrás: vale el último.
        self.assertEqual(
            AnonRateThrottle().get_ident(self._peticion_con("9.9.9.9, 1.2.3.4")), "1.2.3.4"
        )

    def test_el_login_tiene_limite_propio(self):
        ana = crear("ana")
        client = APIClient()
        cache.clear()  # el limitador vive en la caché: sin esto, este test envenena a los demás
        codigos = []
        for _ in range(11):
            res = client.post(
                "/api/auth/login/",
                {"email": "ana@example.com", "password": "no-es-la-buena"},
                format="json",
            )
            codigos.append(res.status_code)
        self.assertIn(429, codigos, "el login tiene que cortar la fuerza bruta")
        self.assertTrue(User.objects.filter(pk=ana.pk).exists())


class CspTests(TestCase):
    """La cabecera Content-Security-Policy no se enviaba **nunca**.

    El proyecto definía `SECURE_CONTENT_SECURITY_POLICY`, que no es un ajuste de Django: nadie
    lo leía, no salía ninguna cabecera y parecía resuelto. Ahora la pone `django-csp`, y estos
    tests fijan justo las directivas que, si desaparecen, rompen la app sin que se note en los
    tests de la API.
    """

    def test_la_cabecera_csp_se_envia(self):
        res = APIClient().get("/api/health/")
        csp = res.headers.get("Content-Security-Policy", "")
        self.assertTrue(csp, "tiene que venir la cabecera")

    def test_lleva_lo_que_la_app_necesita_para_no_romperse(self):
        csp = APIClient().get("/api/health/").headers.get("Content-Security-Policy", "")
        # Sin `wasm-unsafe-eval` no compila el juego del módulo.
        self.assertIn("'wasm-unsafe-eval'", csp)
        # Sin Google no hay botón de inicio de sesión ni tipografías.
        self.assertIn("https://accounts.google.com", csp)
        self.assertIn("https://fonts.gstatic.com", csp)
        # Y las que son puro endurecimiento.
        self.assertIn("object-src 'none'", csp)
        self.assertIn("frame-ancestors 'self'", csp)

    def test_la_politica_de_nginx_y_la_de_django_dicen_lo_mismo(self):
        """El HTML lo sirve nginx y la API la sirve Django: si las dos políticas se separan,
        una de las dos superficies se queda con reglas viejas sin que nadie lo note.

        (Si el fichero de nginx no está al lado —por ejemplo corriendo dentro del contenedor—
        el test se salta: no puede comprobar lo que no ve.)
        """
        import re
        from pathlib import Path

        from django.conf import settings

        ruta = Path(__file__).resolve().parents[2] / "docker" / "nginx-app.conf"
        if not ruta.exists():
            self.skipTest("el nginx.conf no está en este entorno")

        texto = ruta.read_text(encoding="utf-8")
        encontrado = re.search(
            r'add_header Content-Security-Policy "([^"]+)"', texto
        )
        self.assertIsNotNone(encontrado, "nginx tiene que mandar la cabecera")
        de_nginx = {
            parte.split(" ", 1)[0]: sorted(parte.split(" ", 1)[1].split())
            for parte in encontrado.group(1).split("; ")
            if " " in parte
        }
        # `frame-src` y `frame-ancestors` difieren a propósito: Django lleva los orígenes de
        # desarrollo (el `ng serve` que enmarca el juego embebido) cuando DEBUG está activo,
        # y nginx sirve la app construida, donde todo es el mismo origen. El resto tiene que
        # ser idéntico.
        dependen_de_debug = {"frame-src", "frame-ancestors"}
        de_django = {
            k: sorted(v)
            for k, v in settings.CONTENT_SECURITY_POLICY["DIRECTIVES"].items()
            if k not in dependen_de_debug
        }
        self.assertEqual(
            {k: v for k, v in de_nginx.items() if k not in dependen_de_debug}, de_django
        )
        # Y en la app construida el juego embebido es del mismo origen.
        self.assertIn("'self'", de_nginx["frame-ancestors"])

    def test_el_ajuste_que_no_existe_ya_no_esta(self):
        from django.conf import settings

        self.assertFalse(
            hasattr(settings, "SECURE_CONTENT_SECURITY_POLICY"),
            "ese ajuste no lo lee nadie: la política de verdad es CONTENT_SECURITY_POLICY",
        )


class ChatCreateTests(TestCase):
    """`POST /api/chat/messages/` reventaba con un 500."""

    def test_crear_un_mensaje_por_la_lista_da_405(self):
        ana = crear("ana")
        client = APIClient()
        client.force_authenticate(ana)
        res = client.post("/api/chat/messages/", {"content": "hola"}, format="json")
        self.assertEqual(res.status_code, 405)
