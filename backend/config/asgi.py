"""
ASGI config for ft_transcendence project.

Routes HTTP to Django's WSGI/ASGI handler and WebSocket traffic to Channels
consumers (póker, sala del culo y salas de los juegos nuevos).
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# The Django ASGI app must be built before importing anything that touches the
# app registry / models (consumers import models lazily, but routing imports the
# consumer classes at module load).
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import AllowedHostsOriginValidator  # noqa: E402
from django.urls import re_path  # noqa: E402

from apps.culo.consumers import CuloConsumer  # noqa: E402
from apps.poker.consumers import (  # noqa: E402
    PokerMatchmakingConsumer,
    TableConsumer,
)
from apps.salas.consumers import SalaConsumer  # noqa: E402

# Los restos del lobby antiguo (`ws/rooms/`, `ws/matchmaking`, `ws/tournaments`) se han
# quitado: no los usaba nadie (ni el front ni un test) y los dos primeros aceptaban la
# conexión sin autenticar. Un endpoint muerto no es solo ruido: es superficie de ataque.
websocket_urlpatterns = [
    # Póker online autoritativo (Texas Hold'em)
    re_path(r"ws/poker/matchmaking/?$", PokerMatchmakingConsumer.as_asgi()),
    re_path(r"ws/poker/table/(?P<table_id>[^/?]+)/?$", TableConsumer.as_asgi()),
    # Sala del Culo: el código de la sala viaja en la ruta y el JWT en el query string.
    re_path(r"ws/culo/room/(?P<code>[^/?]+)/?$", CuloConsumer.as_asgi()),
    # Salas de los juegos nuevos (genéricas): el juego y el código van en la ruta.
    re_path(r"ws/salas/(?P<juego>[a-z]+)/(?P<code>[^/?]+)/?$", SalaConsumer.as_asgi()),
]

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            URLRouter(websocket_urlpatterns)
        ),
    }
)
