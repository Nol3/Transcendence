"""
URL Configuration for ft_transcendence project.
"""

from pathlib import Path

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from django.views.static import serve as static_serve
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.auth_views import (
    GoogleLoginView,
    LoginView,
    LogoutView,
    MeView,
    RefreshTokenView,
    RegisterView,
)

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
GAME_WEB_DIR = PROJECT_ROOT / "juego" / "web"
GAME_ASSETS_DIR = PROJECT_ROOT / "juego" / "assets"
GAME_ARTIFACT_EXTS = (".wasm", ".js", ".data", ".png", ".otf", ".ttf", ".wav", ".mp3", ".ogg")
GAME_FRAME_ANCESTORS = "frame-ancestors 'self' http://localhost:4200 http://127.0.0.1:4200"


def _apply_game_cache(response, path):
    """Cache WASM build artifacts but force revalidation.

    Filenames are unversioned (index.wasm/.js/.data), so an "immutable"
    policy would pin a stale game in the browser forever after a rebuild.
    static_serve sends Last-Modified, so "no-cache" makes the browser
    revalidate via If-Modified-Since: 304 (cheap) when unchanged, fresh
    bytes after a rebuild.
    """
    if path.lower().endswith(GAME_ARTIFACT_EXTS):
        response["Cache-Control"] = "public, no-cache"
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
    return _apply_game_cache(response, path)


def game_asset_view(request, path):
    """Serve raw game assets (tapete, cards, audio) for use in HTML/CSS."""
    response = static_serve(request, path, document_root=str(GAME_ASSETS_DIR))
    response["Cross-Origin-Resource-Policy"] = "cross-origin"
    response["Access-Control-Allow-Origin"] = "*"
    response["Content-Security-Policy"] = GAME_FRAME_ANCESTORS
    return _apply_game_cache(response, path)




class HealthCheckView(APIView):
    """Comprueba las dependencias del servicio, no solo que Django responda.

    Devuelve 200 si la base de datos y Redis responden, y 503 con el detalle de lo
    que falla. Así el healthcheck de Docker distingue «el proceso vive» de «el
    servicio puede atender».
    """

    permission_classes = []
    authentication_classes = []

    @staticmethod
    def _check_db() -> str:
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return "ok"

    @staticmethod
    def _check_redis() -> str:
        from django.conf import settings

        if not getattr(settings, "REDIS_URL", ""):
            return "no-configurado"
        import redis.asyncio as aioredis
        from asgiref.sync import async_to_sync

        async def ping() -> bool:
            cliente = aioredis.from_url(settings.REDIS_URL)
            try:
                return bool(await cliente.ping())
            finally:
                await cliente.aclose()

        return "ok" if async_to_sync(ping)() else "sin-respuesta"

    def get(self, request):
        from django.utils.translation import get_language

        checks = {}
        for nombre, funcion in (("db", self._check_db), ("redis", self._check_redis)):
            try:
                checks[nombre] = funcion()
            except Exception as exc:                        # noqa: BLE001
                checks[nombre] = f"error: {type(exc).__name__}"
        todo_ok = all(v in ("ok", "no-configurado") for v in checks.values())
        return Response(
            {"status": "healthy" if todo_ok else "degraded", "checks": checks,
             "lang": get_language()},
            status=status.HTTP_200_OK if todo_ok else status.HTTP_503_SERVICE_UNAVAILABLE,
        )


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
    path("api/poker/", include("apps.poker.urls", namespace="poker")),
    path("api/tournament/", include("apps.tournament.urls", namespace="tournament")),
    # Leaderboard
    path("api/leaderboard/", include("apps.users.leaderboard_urls")),
    path("api/leaderboard", include("apps.users.leaderboard_urls")),
    # WASM card game — served directly from juego/web/
    # NOTE: Must not collide with Angular's /game route (SPA client-side route)
    path("game-embed/", game_view),
    path("game-embed/<path:path>", game_view),
    # Raw game assets (tapete, cards, audio) for HTML/CSS use
    path("game-assets/<path:path>", game_asset_view),
    # Redirect root to game embedding MVP
    path("", RedirectView.as_view(url="/game-embed/", permanent=False)),
    # Salas del Culo (Presidente)
    path("api/culo/", include("apps.culo.urls", namespace="culo")),
    # Salas de los juegos nuevos (genéricas: el juego se pide por su id)
    path("api/salas/", include("apps.salas.urls", namespace="salas")),
    # Public API (API key authenticated)
    path("api/public/", include("apps.public_api.urls", namespace="public_api")),
    # Swagger/OpenAPI documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
