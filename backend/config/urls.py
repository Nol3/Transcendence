"""
URL Configuration for ft_transcendence project.
"""

from pathlib import Path
from django.contrib import admin
from django.urls import path, re_path, include
from django.views.generic import RedirectView
from django.views.static import serve as static_serve
from django.views.decorators.clickjacking import xframe_options_exempt
from django.http import JsonResponse
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from drf_spectacular.views import SpectacularSwaggerView, SpectacularAPIView
from apps.users.auth_views import (
    LoginView,
    RegisterView,
    MeView,
    RefreshTokenView,
    LogoutView,
    GoogleLoginView,
)


BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
GAME_WEB_DIR = PROJECT_ROOT / "juego" / "web"
GAME_ASSETS_DIR = PROJECT_ROOT / "juego" / "assets"
IMMUTABLE_GAME_EXTS = (".wasm", ".js", ".data", ".png", ".otf", ".ttf", ".wav", ".mp3", ".ogg")
GAME_FRAME_ANCESTORS = "frame-ancestors 'self' http://localhost:4200 http://127.0.0.1:4200"


def _apply_immutable_cache(response, path):
    """Attach long-lived cache headers when serving WASM build artifacts."""
    if path.lower().endswith(IMMUTABLE_GAME_EXTS):
        response["Cache-Control"] = "public, max-age=31536000, immutable"
    return response


def game_view(request, path=""):
    """Serve the Raylib/WASM card game. CSP frame-ancestors lets Angular embed
    it in an iframe. COOP/COEP headers enable SharedArrayBuffer."""
    if not path:
        path = "index.html"
    response = static_serve(request, path, document_root=str(GAME_WEB_DIR))
    response["Cross-Origin-Opener-Policy"] = "same-origin"
    response["Cross-Origin-Embedder-Policy"] = "require-corp"
    response["Cross-Origin-Resource-Policy"] = "cross-origin"
    response["Content-Security-Policy"] = GAME_FRAME_ANCESTORS
    return _apply_immutable_cache(response, path)


def game_asset_view(request, path):
    """Serve raw game assets (tapete, cards, audio) for use in HTML/CSS."""
    response = static_serve(request, path, document_root=str(GAME_ASSETS_DIR))
    response["Cross-Origin-Resource-Policy"] = "cross-origin"
    response["Access-Control-Allow-Origin"] = "*"
    response["Content-Security-Policy"] = GAME_FRAME_ANCESTORS
    return _apply_immutable_cache(response, path)




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
    path("api/auth/login", LoginView.as_view(), name="auth-login-no-slash"),
    path("api/auth/register/", RegisterView.as_view(), name="auth-register"),
    path("api/auth/register", RegisterView.as_view(), name="auth-register-no-slash"),
    path("api/auth/me/", MeView.as_view(), name="auth-me"),
    path("api/auth/me", MeView.as_view(), name="auth-me-no-slash"),
    path("api/auth/refresh/", RefreshTokenView.as_view(), name="auth-refresh"),
    path("api/auth/refresh", RefreshTokenView.as_view(), name="auth-refresh-no-slash"),
    path("api/auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("api/auth/logout", LogoutView.as_view(), name="auth-logout-no-slash"),
    path("api/auth/google/", GoogleLoginView.as_view(), name="auth-google"),
    path("api/auth/google", GoogleLoginView.as_view(), name="auth-google-no-slash"),
    # API endpoints
    path("api/users/", include("apps.users.urls", namespace="users")),
    path("api/games/", include("apps.games.urls", namespace="games")),
    path("api/chat/", include("apps.chat.urls", namespace="chat")),
    path("api/tournament/", include("apps.tournament.urls", namespace="tournament")),
    # Leaderboard
    path("api/leaderboard/", include("apps.users.leaderboard_urls")),
    path("api/leaderboard", include("apps.users.leaderboard_urls")),
    # WASM card game — served directly from juego/web/
    path("game/", game_view),
    path("game/<path:path>", game_view),
    # Raw game assets (tapete, cards, audio) for HTML/CSS use
    path("game-assets/<path:path>", game_asset_view),
    # Redirect root to game embedding MVP
    path("", RedirectView.as_view(url="/game/", permanent=False)),
    # Public API (API key authenticated)
    path("api/public/", include("apps.public_api.urls", namespace="public_api")),
    # Swagger/OpenAPI documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
