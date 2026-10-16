"""Rutas del historial de póker."""
from django.urls import path

from .views import (
    PokerAchievementsView,
    PokerHandReplayView,
    PokerHistoryView,
    PokerLiveTablesView,
    PokerMatchDetailView,
    PokerPreferencesView,
    PokerStatsView,
)

app_name = 'poker'

urlpatterns = [
    path('history/', PokerHistoryView.as_view(), name='history'),
    path('history/<int:game_id>/', PokerMatchDetailView.as_view(), name='match-detail'),
    path('history/hand/<int:hand_id>/', PokerHandReplayView.as_view(), name='hand-replay'),
    path('stats/', PokerStatsView.as_view(), name='stats'),
    path('achievements/', PokerAchievementsView.as_view(), name='achievements'),
    path('tables/', PokerLiveTablesView.as_view(), name='live-tables'),
    path('preferences/', PokerPreferencesView.as_view(), name='preferences'),
]
