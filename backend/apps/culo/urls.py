"""Rutas de las salas del Culo."""
from django.urls import path

from .views import CuloRoomCreateView, CuloRoomDetailView, CuloRoomJoinView

app_name = "culo"

urlpatterns = [
    path("rooms/", CuloRoomCreateView.as_view(), name="room-create"),
    path("rooms/<str:code>/", CuloRoomDetailView.as_view(), name="room-detail"),
    path("rooms/<str:code>/join/", CuloRoomJoinView.as_view(), name="room-join"),
]
