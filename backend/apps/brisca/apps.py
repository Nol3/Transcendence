"""La app de la Brisca.

Al arrancar Django se importa `juego.py`, que es lo que la registra en la capa de salas.
"""
from django.apps import AppConfig


class BriscaConfig(AppConfig):
    name = "apps.brisca"
    verbose_name = "Brisca"

    def ready(self) -> None:
        from . import juego  # noqa: F401  (registra el juego al importarlo)
