"""Public API serializers."""
from django.contrib.auth.models import User
from rest_framework import serializers

from apps.games.models import Game
from apps.tournament.models import Tournament, TournamentParticipant
from apps.users.models import UserProfile

from .models import ApiKey


# ── API Key management ──────────────────────────────────────────────────────


class ApiKeyCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)


class ApiKeyResponseSerializer(serializers.ModelSerializer):
    """Full key shown once on creation."""

    class Meta:
        model = ApiKey
        fields = ["id", "name", "key", "is_active", "created_at", "last_used_at"]
        read_only_fields = ["id", "key", "is_active", "created_at", "last_used_at"]


class ApiKeyListSerializer(serializers.ModelSerializer):
    """Masked key for list views."""

    masked_key = serializers.CharField(read_only=True)

    class Meta:
        model = ApiKey
        fields = ["id", "name", "masked_key", "is_active", "created_at", "last_used_at"]


# ── Public resource serializers ─────────────────────────────────────────────


class PublicUserSerializer(serializers.ModelSerializer):
    elo_rating = serializers.FloatField(source="profile.elo_rating", default=1600)
    win_count = serializers.IntegerField(source="profile.win_count", default=0)
    loss_count = serializers.IntegerField(source="profile.loss_count", default=0)
    is_online = serializers.BooleanField(source="profile.is_online", default=False)

    class Meta:
        model = User
        fields = ["id", "username", "elo_rating", "win_count", "loss_count", "is_online"]


class PublicGameSerializer(serializers.ModelSerializer):
    player1_username = serializers.CharField(source="player1.username", read_only=True)
    player2_username = serializers.CharField(source="player2.username", read_only=True)
    winner_username = serializers.CharField(
        source="winner.username", read_only=True, allow_null=True
    )

    class Meta:
        model = Game
        fields = [
            "id",
            "player1",
            "player1_username",
            "player2",
            "player2_username",
            "winner",
            "winner_username",
            "status",
            "player1_score",
            "player2_score",
            "played_at",
            "finished_at",
        ]
        read_only_fields = ["id", "played_at"]

    def validate(self, data):
        p1 = data.get("player1")
        p2 = data.get("player2")
        if p1 and p2 and p1 == p2:
            raise serializers.ValidationError("player1 and player2 must be different users.")
        return data


class PublicTournamentSerializer(serializers.ModelSerializer):
    creator_username = serializers.CharField(source="creator.username", read_only=True)
    participant_count = serializers.SerializerMethodField()

    class Meta:
        model = Tournament
        fields = [
            "id",
            "name",
            "description",
            "creator",
            "creator_username",
            "max_players",
            "participant_count",
            "status",
            "created_at",
            "started_at",
            "finished_at",
        ]
        read_only_fields = ["id", "creator", "creator_username", "created_at"]

    def get_participant_count(self, obj):
        return obj.participants.count()
