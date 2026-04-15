"""Public API views — API key authenticated endpoints."""
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.games.models import Game
from apps.tournament.models import Tournament

from .authentication import ApiKeyAuthentication
from .models import ApiKey
from .serializers import (
    ApiKeyCreateSerializer,
    ApiKeyListSerializer,
    ApiKeyResponseSerializer,
    PublicGameSerializer,
    PublicTournamentSerializer,
    PublicUserSerializer,
)
from .throttling import ApiKeyBurstThrottle, ApiKeyThrottle


# ── Helpers ─────────────────────────────────────────────────────────────────

API_KEY_AUTH = [ApiKeyAuthentication]
API_KEY_THROTTLES = [ApiKeyThrottle, ApiKeyBurstThrottle]
JWT_AUTH = [JWTAuthentication]


def _paginate(queryset, request, serializer_class):
    page = max(1, int(request.query_params.get("page", 1)))
    limit = min(100, max(1, int(request.query_params.get("limit", 20))))
    total = queryset.count()
    start = (page - 1) * limit
    data = serializer_class(queryset[start : start + limit], many=True).data
    return Response(
        {
            "data": data,
            "meta": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": (total + limit - 1) // limit if total else 1,
            },
        }
    )


# ── Documentation ────────────────────────────────────────────────────────────


@api_view(["GET"])
@authentication_classes([])
@permission_classes([])
def api_docs(request):
    """Public API documentation — no auth required."""
    base = request.build_absolute_uri("/api/public")
    return Response(
        {
            "name": "Transcendence Public API",
            "version": "1.0",
            "description": (
                "External API for Transcendence game platform. "
                "Authenticate with X-API-Key header. "
                "Rate limit: 100 req/hour, 20 req/minute burst per key."
            ),
            "authentication": {
                "type": "API Key",
                "header": "X-API-Key",
                "obtain": "POST /api/public/keys/ (requires JWT Bearer token)",
            },
            "rate_limits": {
                "hourly": "100 requests / hour per key",
                "burst": "20 requests / minute per key",
            },
            "endpoints": {
                "documentation": {"GET": f"{base}/docs/"},
                "api_keys": {
                    "GET": f"{base}/keys/",
                    "POST": f"{base}/keys/",
                    "DELETE": f"{base}/keys/{{id}}/",
                },
                "users": {
                    "GET (list)": f"{base}/users/",
                    "GET (detail)": f"{base}/users/{{id}}/",
                },
                "games": {
                    "GET (list)": f"{base}/games/",
                    "GET (detail)": f"{base}/games/{{id}}/",
                    "POST": f"{base}/games/",
                    "PUT": f"{base}/games/{{id}}/",
                    "DELETE": f"{base}/games/{{id}}/",
                },
                "tournaments": {
                    "GET (list)": f"{base}/tournaments/",
                    "GET (detail)": f"{base}/tournaments/{{id}}/",
                    "POST": f"{base}/tournaments/",
                    "PUT": f"{base}/tournaments/{{id}}/",
                    "DELETE": f"{base}/tournaments/{{id}}/",
                },
                "leaderboard": {"GET": f"{base}/leaderboard/"},
            },
        }
    )


# ── API Key management (JWT-protected) ──────────────────────────────────────


class ApiKeyListCreateView(APIView):
    """List and create API keys for the authenticated user (JWT required)."""

    authentication_classes = JWT_AUTH
    permission_classes = [IsAuthenticated]

    def get(self, request):
        keys = ApiKey.objects.filter(user=request.user)
        return Response({"data": ApiKeyListSerializer(keys, many=True).data})

    def post(self, request):
        s = ApiKeyCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        key = ApiKey.objects.create(user=request.user, name=s.validated_data["name"])
        return Response(
            {"data": ApiKeyResponseSerializer(key).data},
            status=status.HTTP_201_CREATED,
        )


class ApiKeyDetailView(APIView):
    """Revoke (delete) an API key — only the owner can do this."""

    authentication_classes = JWT_AUTH
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            key = ApiKey.objects.get(pk=pk, user=request.user)
        except ApiKey.DoesNotExist:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        key.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Users (API key required) ─────────────────────────────────────────────────


class PublicUserListView(APIView):
    authentication_classes = API_KEY_AUTH
    permission_classes = [IsAuthenticated]
    throttle_classes = API_KEY_THROTTLES

    def get(self, request):
        users = User.objects.select_related("profile").filter(profile__isnull=False)
        return _paginate(users, request, PublicUserSerializer)


class PublicUserDetailView(APIView):
    authentication_classes = API_KEY_AUTH
    permission_classes = [IsAuthenticated]
    throttle_classes = API_KEY_THROTTLES

    def get(self, request, pk):
        try:
            user = User.objects.select_related("profile").get(pk=pk)
        except User.DoesNotExist:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"data": PublicUserSerializer(user).data})


# ── Games (API key required) ─────────────────────────────────────────────────


class PublicGameListView(APIView):
    authentication_classes = API_KEY_AUTH
    permission_classes = [IsAuthenticated]
    throttle_classes = API_KEY_THROTTLES

    def get(self, request):
        games = Game.objects.select_related("player1", "player2", "winner").all()
        status_filter = request.query_params.get("status")
        if status_filter:
            games = games.filter(status=status_filter)
        return _paginate(games, request, PublicGameSerializer)

    def post(self, request):
        s = PublicGameSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        game = s.save()
        return Response({"data": PublicGameSerializer(game).data}, status=status.HTTP_201_CREATED)


class PublicGameDetailView(APIView):
    authentication_classes = API_KEY_AUTH
    permission_classes = [IsAuthenticated]
    throttle_classes = API_KEY_THROTTLES

    def _get_game(self, pk):
        try:
            return Game.objects.select_related("player1", "player2", "winner").get(pk=pk)
        except Game.DoesNotExist:
            return None

    def get(self, request, pk):
        game = self._get_game(pk)
        if not game:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"data": PublicGameSerializer(game).data})

    def put(self, request, pk):
        game = self._get_game(pk)
        if not game:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        s = PublicGameSerializer(game, data=request.data)
        s.is_valid(raise_exception=True)
        s.save()
        return Response({"data": PublicGameSerializer(game).data})

    def patch(self, request, pk):
        game = self._get_game(pk)
        if not game:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        s = PublicGameSerializer(game, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response({"data": PublicGameSerializer(game).data})

    def delete(self, request, pk):
        game = self._get_game(pk)
        if not game:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        game.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Tournaments (API key required) ───────────────────────────────────────────


class PublicTournamentListView(APIView):
    authentication_classes = API_KEY_AUTH
    permission_classes = [IsAuthenticated]
    throttle_classes = API_KEY_THROTTLES

    def get(self, request):
        tournaments = Tournament.objects.select_related("creator").prefetch_related("participants")
        status_filter = request.query_params.get("status")
        if status_filter:
            tournaments = tournaments.filter(status=status_filter)
        return _paginate(tournaments, request, PublicTournamentSerializer)

    def post(self, request):
        s = PublicTournamentSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        tournament = s.save(creator=request.user)
        return Response(
            {"data": PublicTournamentSerializer(tournament).data},
            status=status.HTTP_201_CREATED,
        )


class PublicTournamentDetailView(APIView):
    authentication_classes = API_KEY_AUTH
    permission_classes = [IsAuthenticated]
    throttle_classes = API_KEY_THROTTLES

    def _get_tournament(self, pk):
        try:
            return Tournament.objects.select_related("creator").prefetch_related("participants").get(pk=pk)
        except Tournament.DoesNotExist:
            return None

    def get(self, request, pk):
        t = self._get_tournament(pk)
        if not t:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"data": PublicTournamentSerializer(t).data})

    def put(self, request, pk):
        t = self._get_tournament(pk)
        if not t:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        s = PublicTournamentSerializer(t, data=request.data)
        s.is_valid(raise_exception=True)
        s.save()
        return Response({"data": PublicTournamentSerializer(t).data})

    def patch(self, request, pk):
        t = self._get_tournament(pk)
        if not t:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        s = PublicTournamentSerializer(t, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response({"data": PublicTournamentSerializer(t).data})

    def delete(self, request, pk):
        t = self._get_tournament(pk)
        if not t:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        t.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Leaderboard (API key required) ───────────────────────────────────────────


class PublicLeaderboardView(APIView):
    authentication_classes = API_KEY_AUTH
    permission_classes = [IsAuthenticated]
    throttle_classes = API_KEY_THROTTLES

    def get(self, request):
        page = max(1, int(request.query_params.get("page", 1)))
        limit = min(100, max(1, int(request.query_params.get("limit", 20))))

        users = (
            User.objects.select_related("profile")
            .filter(profile__isnull=False)
            .order_by("-profile__elo_rating")
        )
        total = users.count()
        start = (page - 1) * limit
        entries = []
        for rank, user in enumerate(users[start : start + limit], start=start + 1):
            p = user.profile
            total_games = p.win_count + p.loss_count
            entries.append(
                {
                    "rank": rank,
                    "id": user.id,
                    "username": user.username,
                    "elo_rating": p.elo_rating,
                    "wins": p.win_count,
                    "losses": p.loss_count,
                    "win_rate": round((p.win_count / total_games * 100) if total_games else 0, 1),
                    "is_online": p.is_online,
                }
            )
        return Response(
            {
                "data": entries,
                "meta": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "total_pages": (total + limit - 1) // limit if total else 1,
                },
            }
        )
