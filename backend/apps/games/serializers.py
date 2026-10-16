"""Games app serializers."""
from rest_framework import serializers

from apps.users.serializers import PublicUserSerializer

from .models import Game


class GameSerializer(serializers.ModelSerializer):
    player1 = PublicUserSerializer(read_only=True)
    player2 = PublicUserSerializer(read_only=True)
    winner = PublicUserSerializer(read_only=True)

    class Meta:
        model = Game
        fields = ['id', 'player1', 'player2', 'winner', 'status', 'player1_score',
                  'player2_score', 'rated', 'played_at', 'finished_at']
        # El resultado y si la partida puntúa los decide el servidor, nunca el cliente:
        # dejarlos escribibles permitía `PATCH {"rated": true}` y declararse ganador para
        # fabricar ELO (el agujero que ya se había cerrado por otra puerta).
        read_only_fields = ['status', 'player1_score', 'player2_score', 'rated',
                            'played_at', 'finished_at']


class GameFinishSerializer(serializers.Serializer):
    """Validates the result reported by the WASM game when a match ends."""
    winner = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, max_length=150,
    )
    player1_score = serializers.IntegerField(min_value=0, default=0)
    player2_score = serializers.IntegerField(min_value=0, default=0)
