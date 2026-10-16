"""La app del Mus.

Al arrancar Django se importa `juego.py`, que es lo que la registra en la capa de salas.
"""
from django.apps import AppConfig


class MusConfig(AppConfig):
    name = "apps.mus"
    verbose_name = "Mus"

    def ready(self) -> None:
        from . import juego  # noqa: F401  (registra el juego al importarlo)
