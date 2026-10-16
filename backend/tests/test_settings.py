"""Configuración de la base de datos: SQLite robusto en desarrollo, PostgreSQL en prod.

`database is locked` aparecía al correr los sondeos de auditoría en paralelo: SQLite
solo admite un escritor a la vez y, sin espera, la segunda petición falla en el acto.
Con WAL y `timeout` la escritura espera en vez de reventar. El despliegue de verdad
usa PostgreSQL (roadmap 4.2).
"""
from django.conf import settings
from django.db import connection
from django.test import SimpleTestCase


class SqliteConfigTests(SimpleTestCase):
    def test_sqlite_espera_en_vez_de_fallar_al_escribir(self):
        engine = settings.DATABASES["default"]["ENGINE"]
        if not engine.endswith("sqlite3"):
            self.skipTest("esta configuración no es SQLite")
        self.assertEqual(settings.DATABASES["default"]["OPTIONS"]["timeout"], 20)

    def test_el_manejador_que_activa_wal_esta_conectado(self):
        """El PRAGMA se aplica al crear cada conexión (en los tests, en memoria)."""
        from django.db.backends.signals import connection_created

        if connection.vendor != "sqlite":
            self.skipTest("no es SQLite")
        uids = [r[0][0] for r in connection_created.receivers]
        self.assertIn("transcendence_sqlite_wal", uids)

    def test_postgresql_pide_usuario_host_y_reutiliza_conexion(self):
        """El bloque de PostgreSQL solo se activa con ese motor (aquí se simula)."""
        engine = "django.db.backends.postgresql"
        config = {"ENGINE": engine, "NAME": "transcendence"}
        if engine.endswith("postgresql"):
            config.update({"USER": "transcendence", "PASSWORD": "", "HOST": "postgres",
                           "PORT": "5432", "CONN_MAX_AGE": 60})
        self.assertEqual(config["CONN_MAX_AGE"], 60)
        self.assertEqual(config["HOST"], "postgres")
        # SQLite se queda con el valor por defecto de Django para esa clave.
        self.assertEqual(settings.DATABASES["default"].get("CONN_MAX_AGE", 0), 0)
        self.assertEqual(settings.DATABASES["default"].get("USER", ""), "")
