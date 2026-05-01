"""Users app views."""

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth.models import User
from .models import UserProfile
from .serializers import UserSerializer, UserUpdateSerializer
from apps.games.models import Game


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet for User management."""

    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == "update_profile":
            return UserUpdateSerializer
        return UserSerializer

    @action(detail=False, methods=["get"], url_path="me")
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

    def _build_stats(self, user):
        """Compute stats for any user. Returns camelCase dict."""
        profile, _ = UserProfile.objects.get_or_create(user=user)
        wins = profile.win_count
        losses = profile.loss_count
        games_played = wins + losses
        win_rate = round((wins / games_played * 100) if games_played > 0 else 0, 1)

        won_games = Game.objects.filter(winner=user, status="finished")
        max_streak = 0
        temp_streak = 0
        for _ in won_games.order_by("finished_at")[:100]:
            temp_streak += 1
            if temp_streak > max_streak:
                max_streak = temp_streak

        rank = User.objects.filter(profile__elo_rating__gt=profile.elo_rating).count() + 1

        return {
            "wins": wins,
            "losses": losses,
            "rank": rank,
            "winRate": win_rate,
            "gamesPlayed": games_played,
            "currentStreak": temp_streak,
            "longestStreak": max_streak,
        }

    @action(detail=False, methods=["get"], url_path="me/stats")
    def stats(self, request):
        """Get current user's stats."""
        return Response({"data": self._build_stats(request.user), "error": None})

    @action(detail=True, methods=["get"], url_path="stats")
    def user_stats(self, request, pk=None):
        """Get stats for a specific user by pk."""
        try:
            target = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"data": self._build_stats(target), "error": None})

    def _build_history_page(self, request, user, page, limit):
        """Build paginated game history for any user."""
        games_as_p1 = Game.objects.filter(player1=user, status="finished")
        games_as_p2 = Game.objects.filter(player2=user, status="finished")
        all_games = (
            (games_as_p1 | games_as_p2)
            .distinct()
            .order_by("-finished_at", "-played_at")
        )
        total = all_games.count()
        start = (page - 1) * limit
        games_page = all_games[start : start + limit]

        history = []
        for game in games_page:
            opponent = game.player2 if game.player1 == user else game.player1
            result = (
                "win" if game.winner == user else "loss" if game.winner else "draw"
            )
            score = (
                f"{game.player1_score}-{game.player2_score}"
                if game.player1 == user
                else f"{game.player2_score}-{game.player1_score}"
            )
            history.append(
                {
                    "id": str(game.id),
                    "result": result,
                    "opponent": {
                        "id": opponent.id,
                        "username": opponent.username,
                        "avatar": request.build_absolute_uri(opponent.profile.avatar.url)
                        if hasattr(opponent, "profile") and opponent.profile.avatar
                        else None,
                    },
                    "score": score,
                    "playedAt": game.finished_at or game.played_at,
                }
            )
        return history, total

    @action(detail=False, methods=["get"], url_path="me/history")
    def history(self, request):
        """Get current user's game history."""
        page = int(request.query_params.get("page", 1))
        limit = int(request.query_params.get("limit", 20))
        history, total = self._build_history_page(request, request.user, page, limit)
        return Response(
            {
                "data": history,
                "meta": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "totalPages": (total + limit - 1) // limit if total > 0 else 1,
                },
                "error": None,
            }
        )

    @action(detail=True, methods=["get"], url_path="history")
    def user_history(self, request, pk=None):
        """Get game history for a specific user by pk."""
        try:
            target = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        page = int(request.query_params.get("page", 1))
        limit = int(request.query_params.get("limit", 20))
        history, total = self._build_history_page(request, target, page, limit)
        return Response(
            {
                "data": history,
                "meta": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "totalPages": (total + limit - 1) // limit if total > 0 else 1,
                },
                "error": None,
            }
        )

    @action(detail=False, methods=["patch"], url_path="me/update_profile")
    def update_profile(self, request):
        """Update current user's profile."""
        try:
            user = request.user
            if not user or user.is_anonymous:
                return Response({
                    "data": None,
                    "error": "Authentication required"
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            profile, _ = UserProfile.objects.get_or_create(user=user)

            username = request.data.get("username")
            if username and username != user.username:
                if User.objects.filter(username=username).exclude(id=user.id).exists():
                    return Response({
                        "data": None,
                        "error": "Username already taken"
                    }, status=status.HTTP_400_BAD_REQUEST)
                user.username = username
                user.save()

            avatar = request.FILES.get("avatar")
            if avatar:
                profile.avatar = avatar
                profile.save()

            # Refresh user from DB to get latest data
            user.refresh_from_db()
            serializer = UserSerializer(user, context={"request": request})
            return Response({
                "data": {"user": serializer.data},
                "error": None
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                "data": None,
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


    @action(detail=False, methods=["post"], url_path="me/upload_avatar")
    def upload_avatar(self, request):
        """Upload avatar for current user."""
        try:
            profile, _ = UserProfile.objects.get_or_create(user=request.user)
            avatar = request.FILES.get("avatar")

            if not avatar:
                return Response({
                    "data": None,
                    "error": "No avatar file provided"
                }, status=status.HTTP_400_BAD_REQUEST)

            profile.avatar = avatar
            profile.save()

            avatar_url = request.build_absolute_uri(profile.avatar.url)
            return Response({
                "data": {"avatarUrl": avatar_url},
                "error": None
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                "data": None,
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
