"""
ASGI config for ft_transcendence project.
"""

import os

from django.core.asgi import get_asgi_application
from daphne.routing import ProtocolTypeRouter, URLRouter
from django.urls import path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": URLRouter([
        # WebSocket routes will be added here for real-time features
    ]),
})
