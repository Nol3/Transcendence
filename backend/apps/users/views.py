"""Users app views."""

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from django.contrib.auth.models import User
from django.db.models import Max
from .models import UserProfile
from .serializers import (
    UserSerializer,
    UserProfileSerializer,
    UserStatsSerializer,
    GameHistorySerializer,
)
from apps.games.models import Game


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet for User management."""

    queryset = User.objects.all()
    serializer_class = UserSerializer

    @action(detail=False, methods=["get"])
    def me(self, request):
        """Get current logged-in user."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def register(self, request):
        """Register a new user."""
        username = request.data.get("username")
        email = request.data.get("email")
        password = request.data.get("password")

        if User.objects.filter(username=username).exists():
            return Response(
                {"error": "Username already exists"}, status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.create_user(
            username=username, email=email, password=password
        )
        UserProfile.objects.create(user=user)

        serializer = self.get_serializer(user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Get current user's stats."""
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        wins = profile.win_count
        losses = profile.loss_count
        games_played = wins + losses
        win_rate = round((wins / games_played * 100) if games_played > 0 else 0, 1)

        won_games = Game.objects.filter(winner=request.user, status="finished")
        max_streak = 0
        current_streak = 0
        temp_streak = 0

        for game in won_games.order_by("finished_at")[:100]:
            temp_streak += 1
            if temp_streak > max_streak:
                max_streak = temp_streak
        current_streak = temp_streak

        rank = (
            User.objects.filter(profile__elo_rating__gt=profile.elo_rating).count() + 1
        )

        data = {
            "wins": wins,
            "losses": losses,
            "rank": rank,
            "win_rate": win_rate,
            "games_played": games_played,
            "current_streak": current_streak,
            "longest_streak": max_streak,
        }

        serializer = UserStatsSerializer(data)
        return Response({"data": serializer.data})

    @action(detail=False, methods=["get"])
    def history(self, request):
        """Get current user's game history."""
        page = int(request.query_params.get("page", 1))
        limit = int(request.query_params.get("limit", 20))

        games_as_p1 = Game.objects.filter(player1=request.user, status="finished")
        games_as_p2 = Game.objects.filter(player2=request.user, status="finished")

        all_games = (
            (games_as_p1 | games_as_p2)
            .distinct()
            .order_by("-finished_at", "-played_at")
        )

        total = all_games.count()
        start = (page - 1) * limit
        end = start + limit
        games_page = all_games[start:end]

        history = []
        for game in games_page:
            opponent = game.player2 if game.player1 == request.user else game.player1
            result = (
                "win"
                if game.winner == request.user
                else "loss"
                if game.winner
                else "draw"
            )
            score = (
                f"{game.player1_score}-{game.player2_score}"
                if game.player1 == request.user
                else f"{game.player2_score}-{game.player1_score}"
            )

            history.append(
                {
                    "id": str(game.id),
                    "result": result,
                    "opponent": {
                        "id": opponent.id,
                        "username": opponent.username,
                        "avatar": request.build_absolute_uri(
                            opponent.profile.avatar.url
                        )
                        if hasattr(opponent, "profile") and opponent.profile.avatar
                        else None,
                    },
                    "score": score,
                    "played_at": game.finished_at or game.played_at,
                }
            )

        return Response(
            {
                "data": history,
                "meta": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "totalPages": (total + limit - 1) // limit if total > 0 else 1,
                },
            }
        )

    @action(detail=False, methods=["patch"])
    def update_profile(self, request):
        """Update current user's profile."""
        user = request.user
        profile, _ = UserProfile.objects.get_or_create(user=user)

        username = request.data.get("username")
        if username and username != user.username:
            if User.objects.filter(username=username).exclude(id=user.id).exists():
                return Response(
                    {"error": "Username already taken"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user.username = username
            user.save()

        avatar = request.FILES.get("avatar")
        if avatar:
            profile.avatar = avatar
            profile.save()

        serializer = self.get_serializer(user)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="upload_avatar")
    def upload_avatar(self, request):
        """Upload avatar for current user."""
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        avatar = request.FILES.get("avatar")

        if not avatar:
            return Response(
                {"error": "No avatar file provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        profile.avatar = avatar
        profile.save()

        return Response({"avatar": request.build_absolute_uri(profile.avatar.url)})
