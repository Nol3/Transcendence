"""La app del Mentiroso.

Al arrancar Django se importa `juego.py`, que es lo que la registra en la capa de salas: así el
Mentiroso se puede jugar online sin que nadie tenga que acordarse de enchufarlo.
"""
from django.apps import AppConfig


class MentirosoConfig(AppConfig):
    name = "apps.mentiroso"
    verbose_name = "Mentiroso"

    def ready(self) -> None:
        from . import juego  # noqa: F401  (registra el juego al importarlo)
