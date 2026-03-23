"""Games app serializers."""
from rest_framework import serializers
from .models import Game
from apps.users.serializers import UserSerializer


class GameSerializer(serializers.ModelSerializer):
    player1 = UserSerializer(read_only=True)
    player2 = UserSerializer(read_only=True)
    winner = UserSerializer(read_only=True)

    class Meta:
        model = Game
        fields = ['id', 'player1', 'player2', 'winner', 'status', 'player1_score', 'player2_score', 'played_at', 'finished_at']
