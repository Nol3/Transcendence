"""API de las salas: crear, mirar y entrar.

El juego va por WebSocket; aquí solo está lo que hace falta **antes** de conectarse: crear la sala
y mirar cómo está por su código (para poder avisar de «esa sala no existe» antes de abrir el
socket). Es genérico: el juego se pide por su id.
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .juegos import JUEGOS
from .juegos import get as get_juego
from .rooms import SalaError, registry


class SalaCreateView(APIView):
    """`POST /api/salas/` — crea una sala del juego pedido y devuelve su código."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        juego_id = str(request.data.get("juego") or "").strip().lower()
        if juego_id not in JUEGOS:
            return Response(
                {"error": "Ese juego no existe", "juegos": sorted(JUEGOS)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        opciones = request.data.get("opciones") or {}
        if not isinstance(opciones, dict):
            return Response({"error": "Las opciones van como objeto"},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            sala = registry.create(request.user.id, juego_id, opciones)
        except SalaError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_409_CONFLICT)
        sala.join(request.user.id, request.user.username)
        juego = get_juego(juego_id)
        return Response(
            {
                "code": sala.code,
                "juego": sala.juego_id,
                "status": sala.status,
                "opciones": sala.opciones,
                "maxPlayers": juego.max_jugadores,
                "minPlayers": juego.min_jugadores,
            },
            status=status.HTTP_201_CREATED,
        )


class SalaDetailView(APIView):
    """`GET /api/salas/<code>/` — cómo está una sala, por su código."""

    permission_classes = [IsAuthenticated]

    def get(self, request, code: str):
        sala = registry.get(code)
        if sala is None:
            return Response({"error": "Esa sala no existe o ya se ha cerrado"},
                            status=status.HTTP_404_NOT_FOUND)
        return Response(sala.to_dict(viewer_id=request.user.id))


class SalaJoinView(APIView):
    """`POST /api/salas/<code>/join/` — entrar en una sala antes de conectar.

    Se puede entrar directamente por WebSocket, pero pasar por aquí permite comprobar el código y
    devolver un error claro si la sala no existe o está llena.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, code: str):
        sala = registry.get(code)
        if sala is None:
            return Response({"error": "Esa sala no existe o ya se ha cerrado"},
                            status=status.HTTP_404_NOT_FOUND)
        try:
            sala.join(request.user.id, request.user.username)
        except SalaError as exc:
            return Response({"error": str(exc), "code": exc.code},
                            status=status.HTTP_409_CONFLICT)
        return Response(sala.to_dict(viewer_id=request.user.id))


class SalaGamesView(APIView):
    """`GET /api/salas/juegos/` — qué juegos se pueden jugar online ahora mismo."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            jid: {
                "minPlayers": j.min_jugadores,
                "maxPlayers": j.max_jugadores,
                "opciones": j.opciones,
            }
            for jid, j in sorted(JUEGOS.items())
        })
