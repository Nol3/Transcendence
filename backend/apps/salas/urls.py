"""Rutas de las salas (comunes a todos los juegos)."""
from django.urls import path

from .views import SalaCreateView, SalaDetailView, SalaGamesView, SalaJoinView

app_name = "salas"

urlpatterns = [
    path("", SalaCreateView.as_view(), name="create"),
    path("juegos/", SalaGamesView.as_view(), name="games"),
    path("<str:code>/", SalaDetailView.as_view(), name="detail"),
    path("<str:code>/join/", SalaJoinView.as_view(), name="join"),
]
