"""La app del Tute.

Al arrancar Django se importa `juego.py`, que es lo que la registra en la capa de salas.
"""
from django.apps import AppConfig


class TuteConfig(AppConfig):
    name = "apps.tute"
    verbose_name = "Tute"

    def ready(self) -> None:
        from . import juego  # noqa: F401  (registra el juego al importarlo)
