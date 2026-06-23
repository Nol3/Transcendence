"""
ASGI config for ft_transcendence project.

Routes HTTP to Django's WSGI/ASGI handler and WebSocket traffic to Channels
consumers (live tournament brackets, game rooms, matchmaking).
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

from apps.games.consumers import MatchmakingConsumer, RoomConsumer  # noqa: E402
from apps.tournament.consumers import TournamentConsumer  # noqa: E402

websocket_urlpatterns = [
    re_path(r"ws/rooms/(?P<room_id>[^/?]+)/?$", RoomConsumer.as_asgi()),
    re_path(r"ws/matchmaking/?$", MatchmakingConsumer.as_asgi()),
    re_path(r"ws/tournaments/(?P<tournament_id>[^/?]+)/?$", TournamentConsumer.as_asgi()),
]

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            URLRouter(websocket_urlpatterns)
        ),
    }
)
