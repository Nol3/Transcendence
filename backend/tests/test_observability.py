"""Observabilidad (4.4): logs en JSON, request id y health que distingue fallos."""
import json
import logging
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings

from config.observability import HEADER, JsonFormatter, RequestIdMiddleware, request_id_var
from config.urls import HealthCheckView


class JsonFormatterTests(SimpleTestCase):
    def _registro(self, mensaje="hola", **extra):
        record = logging.LogRecord(
            name="apps.poker", level=logging.INFO, pathname=__file__, lineno=1,
            msg=mensaje, args=(), exc_info=None,
        )
        if extra:
            record.extra_fields = extra
        return record

    def test_la_linea_es_json_con_nivel_y_logger(self):
        linea = JsonFormatter().format(self._registro("mesa creada"))
        datos = json.loads(linea)
        self.assertEqual(datos["level"], "INFO")
        self.assertEqual(datos["logger"], "apps.poker")
        self.assertEqual(datos["message"], "mesa creada")
        self.assertIn("time", datos)

    def test_lleva_el_request_id_de_la_peticion(self):
        token = request_id_var.set("abc123")
        try:
            datos = json.loads(JsonFormatter().format(self._registro()))
        finally:
            request_id_var.reset(token)
        self.assertEqual(datos["request_id"], "abc123")

    def test_sin_peticion_el_id_es_un_guion(self):
        datos = json.loads(JsonFormatter().format(self._registro()))
        self.assertEqual(datos["request_id"], "-")

    def test_los_campos_extra_van_al_json(self):
        datos = json.loads(JsonFormatter().format(self._registro(mesa="t-1", asientos=6)))
        self.assertEqual(datos["mesa"], "t-1")
        self.assertEqual(datos["asientos"], 6)

    def test_una_excepcion_se_incluye_como_texto(self):
        try:
            raise ValueError("boom")
        except ValueError:
            import sys

            record = logging.LogRecord(
                name="apps.poker", level=logging.ERROR, pathname=__file__, lineno=1,
                msg="falló", args=(), exc_info=sys.exc_info(),
            )
        datos = json.loads(JsonFormatter().format(record))
        self.assertIn("ValueError: boom", datos["exc"])


class RequestIdMiddlewareTests(SimpleTestCase):
    def _peticion(self, rid=None):
        class Peticion:
            headers = {HEADER: rid} if rid else {}

        return Peticion()

    def test_genera_un_id_y_lo_devuelve_en_la_respuesta(self):
        visto = {}

        def vista(request):
            visto["durante"] = request_id_var.get()
            visto["en_request"] = request.request_id

            class Respuesta(dict):
                pass

            return Respuesta()

        respuesta = RequestIdMiddleware(vista)(self._peticion())
        self.assertEqual(visto["durante"], visto["en_request"])
        self.assertEqual(respuesta[HEADER], visto["durante"])
        self.assertTrue(visto["durante"])

    def test_respeta_el_id_que_manda_el_proxy(self):
        def vista(request):
            return {}

        respuesta = RequestIdMiddleware(vista)(self._peticion("del-proxy"))
        self.assertEqual(respuesta[HEADER], "del-proxy")

    def test_al_acabar_la_peticion_el_id_se_limpia(self):
        def vista(request):
            return {}

        RequestIdMiddleware(vista)(self._peticion("x"))
        self.assertEqual(request_id_var.get(), "-")


class HealthCheckTests(TestCase):
    def test_con_todo_en_pie_dice_healthy(self):
        respuesta = self.client.get("/api/health/")
        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertEqual(datos["status"], "healthy")
        self.assertEqual(datos["checks"]["db"], "ok")

    def test_sin_redis_configurado_no_lo_cuenta_como_fallo(self):
        # El escenario se fuerza a propósito: no se puede dar por hecho que el entorno
        # no tenga REDIS_URL. Dentro del contenedor sí la tiene (y el test fallaba solo
        # por eso, que es justo el tipo de fallo que depende de dónde se corra).
        with self.settings(REDIS_URL=""):
            datos = self.client.get("/api/health/").json()
        self.assertEqual(datos["checks"]["redis"], "no-configurado")

    def test_con_redis_configurado_comprueba_el_ping(self):
        class ClienteFalso:
            async def ping(self):
                return True

            async def aclose(self):
                pass

        with (
            override_settings(REDIS_URL="redis://localhost:6379/0"),
            patch("redis.asyncio.from_url", return_value=ClienteFalso()),
        ):
            self.assertEqual(HealthCheckView._check_redis(), "ok")

    def test_si_redis_no_responde_lo_dice(self):
        class ClienteMudo:
            async def ping(self):
                return False

            async def aclose(self):
                pass

        with (
            override_settings(REDIS_URL="redis://localhost:6379/0"),
            patch("redis.asyncio.from_url", return_value=ClienteMudo()),
        ):
            self.assertEqual(HealthCheckView._check_redis(), "sin-respuesta")

    def test_si_la_base_de_datos_falla_devuelve_503(self):
        with patch("config.urls.HealthCheckView._check_db",
                   side_effect=RuntimeError("db caída")):
            respuesta = self.client.get("/api/health/")
        self.assertEqual(respuesta.status_code, 503)
        datos = respuesta.json()
        self.assertEqual(datos["status"], "degraded")
        self.assertIn("error", datos["checks"]["db"])
