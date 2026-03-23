"""Games app views."""
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Game
from .serializers import GameSerializer


class GameViewSet(viewsets.ModelViewSet):
    """ViewSet for Game management."""
    queryset = Game.objects.all()
    serializer_class = GameSerializer

    @action(detail=False, methods=['get'])
    def my_games(self, request):
        """Get games for the current user."""
        games = Game.objects.filter(
            models.Q(player1=request.user) | models.Q(player2=request.user)
        )
        serializer = self.get_serializer(games, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def create_game(self, request):
        """Create a new game."""
        player2_id = request.data.get('player2_id')
        game = Game.objects.create(
            player1=request.user,
            player2_id=player2_id
        )
        serializer = self.get_serializer(game)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
