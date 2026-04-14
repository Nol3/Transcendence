"""
URL Configuration for ft_transcendence project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from apps.users.auth_views import (
    LoginView,
    RegisterView,
    MeView,
    RefreshTokenView,
    LogoutView,
)


class HealthCheckView(APIView):
    """Health check endpoint for Docker containers."""

    permission_classes = []
    authentication_classes = []

    def get(self, request):
        return Response({"status": "healthy"}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([])
def api_root(request):
    """API root endpoint."""
    return Response(
        {
            "message": "Welcome to Transcendence API",
            "version": "1.0",
            "endpoints": {
                "auth": "/api/auth/",
                "users": "/api/users/",
                "games": "/api/games/",
                "chat": "/api/chat/",
                "tournament": "/api/tournament/",
                "leaderboard": "/api/leaderboard/",
            },
        }
    )


urlpatterns = [
    path("admin/", admin.site.urls),
    # Health check
    path("api/health/", HealthCheckView.as_view(), name="health-check"),
    # API root
    path("api/", api_root, name="api-root"),
    # Custom Auth endpoints (frontend compatible)
    path("api/auth/login/", LoginView.as_view(), name="auth-login"),
    path("api/auth/register/", RegisterView.as_view(), name="auth-register"),
    path("api/auth/me/", MeView.as_view(), name="auth-me"),
    path("api/auth/refresh/", RefreshTokenView.as_view(), name="auth-refresh"),
    path("api/auth/logout/", LogoutView.as_view(), name="auth-logout"),
    # API endpoints
    path("api/users/", include("apps.users.urls", namespace="users")),
    path("api/games/", include("apps.games.urls", namespace="games")),
    path("api/chat/", include("apps.chat.urls", namespace="chat")),
    path("api/tournament/", include("apps.tournament.urls", namespace="tournament")),
    # Leaderboard
    path("api/leaderboard/", include("apps.users.leaderboard_urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
