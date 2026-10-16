"""API de las salas del Culo.

El juego va por WebSocket; aquí solo está lo que hace falta antes de conectarse: crear la
sala y mirar cómo está una sala por su código (para poder avisar de «esa sala no existe»
antes de abrir el socket).
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .rooms import MAX_JUGADORES, RoomError, registry


class CuloRoomCreateView(APIView):
    """`POST /api/culo/rooms/` — crea una sala y devuelve su código para compartirlo."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            barajas = 2 if int(request.data.get("decks") or 1) == 2 else 1
        except (TypeError, ValueError):
            barajas = 1
        sala = registry.create(request.user.id, barajas)
        sala.join(request.user.id, request.user.username)
        return Response(
            {"code": sala.code, "decks": sala.decks, "status": sala.status,
             "maxPlayers": MAX_JUGADORES},
            status=status.HTTP_201_CREATED,
        )


class CuloRoomDetailView(APIView):
    """`GET /api/culo/rooms/<code>/` — cómo está una sala, por su código."""

    permission_classes = [IsAuthenticated]

    def get(self, request, code: str):
        sala = registry.get(code)
        if sala is None:
            return Response({"error": "Esa sala no existe o ya se ha cerrado"},
                            status=status.HTTP_404_NOT_FOUND)
        return Response(sala.to_dict(viewer_id=request.user.id))


class CuloRoomJoinView(APIView):
    """`POST /api/culo/rooms/<code>/join/` — entrar en una sala antes de conectar.

    Se puede entrar directamente por WebSocket, pero pasar por aquí permite comprobar el
    código y devolver un error claro si la sala no existe o está llena.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, code: str):
        sala = registry.get(code)
        if sala is None:
            return Response({"error": "Esa sala no existe o ya se ha cerrado"},
                            status=status.HTTP_404_NOT_FOUND)
        try:
            sala.join(request.user.id, request.user.username)
        except RoomError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(sala.to_dict(viewer_id=request.user.id))
