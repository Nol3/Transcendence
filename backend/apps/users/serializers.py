"""Users app serializers."""

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            "id",
            "bio",
            "avatar",
            "win_count",
            "loss_count",
            "elo_rating",
            "is_online",
        ]

    def get_avatar(self, obj):
        if obj.avatar and obj.avatar.name:
            try:
                request = self.context.get("request")
                if request:
                    return request.build_absolute_uri(obj.avatar.url)
                return f"/media/{obj.avatar.name}"
            except Exception:
                return None
        return None


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "profile"]


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for PATCH updates - allows partial updates."""
    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name"]
        extra_kwargs = {
            "username": {"required": False},
            "email": {"required": False},
            "first_name": {"required": False},
            "last_name": {"required": False},
        }


class UserStatsSerializer(serializers.Serializer):
    wins = serializers.IntegerField()
    losses = serializers.IntegerField()
    rank = serializers.IntegerField()
    win_rate = serializers.FloatField()
    games_played = serializers.IntegerField()
    current_streak = serializers.IntegerField()
    longest_streak = serializers.IntegerField()


class OpponentSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    avatar = serializers.CharField(allow_null=True)


class GameHistorySerializer(serializers.Serializer):
    id = serializers.CharField()
    result = serializers.ChoiceField(choices=["win", "loss", "draw"])
    opponent = OpponentSerializer()
    score = serializers.CharField()
    played_at = serializers.DateTimeField()


class LeaderboardEntrySerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    user = OpponentSerializer()
    wins = serializers.IntegerField()
    losses = serializers.IntegerField()
    win_rate = serializers.FloatField()
    elo_rating = serializers.FloatField()
