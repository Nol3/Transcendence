"""Public API URL patterns."""
from django.urls import path

from .views import (
    ApiKeyDetailView,
    ApiKeyListCreateView,
    PublicGameDetailView,
    PublicGameListView,
    PublicLeaderboardView,
    PublicTournamentDetailView,
    PublicTournamentListView,
    PublicUserDetailView,
    PublicUserListView,
    api_docs,
)

app_name = "public_api"

urlpatterns = [
    # Documentation (no auth)
    path("docs/", api_docs, name="docs"),
    path("docs", api_docs, name="docs-no-slash"),
    # API Key management (JWT auth)
    path("keys/", ApiKeyListCreateView.as_view(), name="key-list-create"),
    path("keys/<int:pk>/", ApiKeyDetailView.as_view(), name="key-detail"),
    # Users (API key auth)
    path("users/", PublicUserListView.as_view(), name="user-list"),
    path("users/<int:pk>/", PublicUserDetailView.as_view(), name="user-detail"),
    # Games (API key auth) — GET, POST, PUT, PATCH, DELETE
    path("games/", PublicGameListView.as_view(), name="game-list"),
    path("games/<int:pk>/", PublicGameDetailView.as_view(), name="game-detail"),
    # Tournaments (API key auth) — GET, POST, PUT, PATCH, DELETE
    path("tournaments/", PublicTournamentListView.as_view(), name="tournament-list"),
    path("tournaments/<int:pk>/", PublicTournamentDetailView.as_view(), name="tournament-detail"),
    # Leaderboard (API key auth)
    path("leaderboard/", PublicLeaderboardView.as_view(), name="leaderboard"),
]
