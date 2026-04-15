"""Leaderboard views."""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.contrib.auth.models import User
from django.db.models import F
from .serializers import LeaderboardEntrySerializer


class LeaderboardView(APIView):
    """API view for the leaderboard."""

    permission_classes = [AllowAny]

    def get(self, request):
        page = int(request.query_params.get("page", 1))
        limit = int(request.query_params.get("limit", 10))

        users = (
            User.objects.select_related("profile")
            .filter(profile__isnull=False)
            .exclude(profile__elo_rating=0)
            .order_by("-profile__elo_rating")
        )

        total = users.count()
        start = (page - 1) * limit
        end = start + limit
        users_page = users[start:end]

        entries = []
        for rank, user in enumerate(users[start:end], start=start + 1):
            profile = user.profile
            wins = profile.win_count
            losses = profile.loss_count
            total_games = wins + losses
            win_rate = round((wins / total_games * 100) if total_games > 0 else 0, 1)

            entries.append(
                {
                    "rank": rank,
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "avatar": request.build_absolute_uri(profile.avatar.url)
                        if profile.avatar
                        else None,
                    },
                    "wins": wins,
                    "losses": losses,
                    "winRate": win_rate,
                    "eloRating": profile.elo_rating,
                }
            )

        return Response(
            {
                "data": entries,
                "meta": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "totalPages": (total + limit - 1) // limit if total > 0 else 1,
                },
            }
        )
