"""La API responde en el idioma que pide el cliente (roadmap 7.5).

`LocaleMiddleware` elige el idioma a partir de la cabecera `Accept-Language` y lo deja
en `request.LANGUAGE_CODE`. Aquí se comprueba el mecanismo de punta a punta: se pide
`/api/health/` con distintas cabeceras y la respuesta dice en qué idioma ha salido.
"""
from django.conf import settings
from django.test import TestCase
from django.utils import translation
from django.utils.translation import gettext


class ApiLanguageTests(TestCase):
    def test_locale_middleware_esta_instalado(self):
        self.assertIn("django.middleware.locale.LocaleMiddleware", settings.MIDDLEWARE)

    def test_los_idiomas_soportados_son_los_mismos_que_el_front(self):
        codigos = [codigo for codigo, _ in settings.LANGUAGES]
        self.assertEqual(sorted(codigos), ["en", "es", "fr"])

    def test_la_respuesta_sale_en_el_idioma_que_pide_la_cabecera(self):
        casos = {
            "es-ES,es;q=0.9,en;q=0.8": "es",
            "fr-FR,fr;q=0.9": "fr",
            "en-GB,en;q=0.9": "en",
        }
        for cabecera, esperado in casos.items():
            respuesta = self.client.get("/api/health/", headers={"accept-language": cabecera})
            self.assertEqual(respuesta.json()["lang"], esperado, f"con «{cabecera}»")

    def test_sin_cabecera_usa_el_idioma_por_defecto(self):
        respuesta = self.client.get("/api/health/")
        self.assertEqual(respuesta.json()["lang"], settings.LANGUAGE_CODE.split("-")[0])

    def test_una_cabecera_de_un_idioma_que_no_soportamos_no_rompe(self):
        respuesta = self.client.get("/api/health/", headers={"accept-language": "de-DE,de;q=0.9"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["lang"], settings.LANGUAGE_CODE.split("-")[0])


class MensajesTraducidosTests(TestCase):
    """Los mensajes de error de la API salen en el idioma que pide el cliente."""

    CASOS = {
        "es": "Credenciales incorrectas",
        "en": "Invalid credentials",
        "fr": "Identifiants incorrects",
    }

    def test_el_catalogo_tiene_las_tres_lenguas(self):
        for lang, esperado in self.CASOS.items():
            with translation.override(lang):
                self.assertEqual(str(gettext("Invalid credentials")), esperado, f"en {lang}")

    def test_un_error_de_login_sale_en_el_idioma_pedido(self):
        for lang, esperado in self.CASOS.items():
            respuesta = self.client.post(
                "/api/auth/login/",
                data={"email": "nadie@example.com", "password": "loquesea"},
                content_type="application/json",
                headers={"accept-language": lang},
            )
            self.assertEqual(respuesta.status_code, 401)
            self.assertEqual(respuesta.json()["error"], esperado, f"en {lang}")

    def test_el_mismo_error_sin_cabecera_sale_en_ingles(self):
        respuesta = self.client.post(
            "/api/auth/login/",
            data={"email": "nadie@example.com", "password": "loquesea"},
            content_type="application/json",
        )
        self.assertEqual(respuesta.json()["error"], "Invalid credentials")
