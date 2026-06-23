"""Games app views."""
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth.models import User
from django.db.models import Q

from .models import Game
from .serializers import GameSerializer, GameFinishSerializer
from .services import finish_game, get_ai_opponent


class GameViewSet(viewsets.ModelViewSet):
    """ViewSet for Game management."""
    queryset = Game.objects.all()
    serializer_class = GameSerializer

    @action(detail=False, methods=['get'])
    def my_games(self, request):
        """Get games for the current user."""
        games = Game.objects.filter(
            Q(player1=request.user) | Q(player2=request.user)
        )
        serializer = self.get_serializer(games, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def create_game(self, request):
        """Create a new game.

        `player2_id` is optional: a solo/practice match against the WASM card
        game defaults to the AI opponent so player2 is always a real FK.
        """
        player2_id = request.data.get('player2_id')
        if player2_id:
            player2 = User.objects.filter(pk=player2_id).first()
            if player2 is None:
                return Response(
                    {'error': 'Opponent not found'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            player2 = get_ai_opponent()

        game = Game.objects.create(
            player1=request.user,
            player2=player2,
            status='in_progress',
        )
        serializer = self.get_serializer(game)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def finish(self, request, pk=None):
        """Record the final result and update ELO / win-loss history.

        Body: { "winner": "<username>", "player1_score": int, "player2_score": int }.
        `winner` omitted/blank ⇒ draw. Only the involved players may report.
        """
        game = self.get_object()

        if request.user != game.player1 and request.user != game.player2:
            return Response(
                {'error': 'Not a participant of this game'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = GameFinishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        winner_username = (data.get('winner') or '').strip()
        winner = None
        if winner_username:
            # player1 is the logged-in user. In a local 2–4 player (hotseat)
            # match the winner may be another local player ("Jugador 2"), which
            # maps to the opponent slot from this account's perspective.
            if winner_username == game.player1.username:
                winner = game.player1
            else:
                winner = game.player2

        game = finish_game(
            game,
            winner=winner,
            player1_score=data['player1_score'],
            player2_score=data['player2_score'],
        )
        return Response(self.get_serializer(game).data, status=status.HTTP_200_OK)
