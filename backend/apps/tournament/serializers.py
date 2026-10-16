"""Tournament app serializers."""
from rest_framework import serializers

from apps.users.serializers import PublicUserSerializer

from .models import (
    Tournament,
    TournamentMatch,
    TournamentParticipant,
    TournamentRound,
)


class TournamentParticipantSerializer(serializers.ModelSerializer):
    user = PublicUserSerializer(read_only=True)

    class Meta:
        model = TournamentParticipant
        fields = ['id', 'user', 'is_eliminated', 'joined_at']


class TournamentPlayerSerializer(serializers.Serializer):
    """Lightweight player payload for bracket slots."""
    id = serializers.IntegerField()
    username = serializers.CharField()
    avatar = serializers.SerializerMethodField()

    def get_avatar(self, obj):
        profile = getattr(obj, 'profile', None)
        if profile and profile.avatar and profile.avatar.name:
            request = self.context.get('request')
            try:
                if request:
                    return request.build_absolute_uri(profile.avatar.url)
                return profile.avatar.url
            except Exception:
                return None
        return None


class TournamentMatchSerializer(serializers.ModelSerializer):
    round = serializers.IntegerField(source='round.number', read_only=True)
    player1 = TournamentPlayerSerializer(read_only=True)
    player2 = TournamentPlayerSerializer(read_only=True)
    winner_slot = serializers.SerializerMethodField()
    reported_by = serializers.SerializerMethodField()
    reported_winner_slot = serializers.IntegerField(
        source='result_winner_slot', read_only=True
    )

    class Meta:
        model = TournamentMatch
        fields = [
            'id', 'round', 'position', 'player1', 'player2',
            'winner_slot', 'player1_score', 'player2_score', 'status',
            # resultado pendiente de confirmación (quién y a quién declaró)
            'reported_winner_slot', 'reported_by',
        ]

    def get_reported_by(self, obj):
        """Usuario que declaró el resultado pendiente (solo su nombre)."""
        if obj.result_reported_by_id is None:
            return None
        return {
            'id': obj.result_reported_by_id,
            'username': obj.result_reported_by.username,
        }

    def get_winner_slot(self, obj):
        if obj.winner_id is None:
            return None
        if obj.player1_id and obj.winner_id == obj.player1_id:
            return 1
        if obj.player2_id and obj.winner_id == obj.player2_id:
            return 2
        return None


class TournamentRoundSerializer(serializers.ModelSerializer):
    matches = TournamentMatchSerializer(many=True, read_only=True)

    class Meta:
        model = TournamentRound
        fields = ['id', 'number', 'name', 'matches']


class TournamentSerializer(serializers.ModelSerializer):
    creator = PublicUserSerializer(read_only=True)
    winner = PublicUserSerializer(read_only=True)
    participants = TournamentParticipantSerializer(many=True, read_only=True)
    rounds = TournamentRoundSerializer(many=True, read_only=True)

    class Meta:
        model = Tournament
        fields = [
            'id', 'name', 'description', 'creator', 'max_players', 'status',
            'winner', 'created_at', 'started_at', 'finished_at',
            'participants', 'rounds',
        ]


class TournamentCreateSerializer(serializers.Serializer):
    """Validates tournament creation input before persisting."""
    name = serializers.CharField(min_length=3, max_length=100, trim_whitespace=True)
    description = serializers.CharField(
        required=False, allow_blank=True, max_length=500, default=''
    )
    max_players = serializers.IntegerField(min_value=4, max_value=32)


class MatchResultSerializer(serializers.Serializer):
    """Validates a reported tournament match result."""
    winner_slot = serializers.ChoiceField(choices=[1, 2])
    player1_score = serializers.IntegerField(min_value=0, default=0)
    player2_score = serializers.IntegerField(min_value=0, default=0)
