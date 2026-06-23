"""Users app serializers."""

from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import RegexValidator
from .models import UserProfile


USERNAME_VALIDATOR = RegexValidator(
    regex=r"^[a-zA-Z0-9_]+$",
    message="Username may only contain letters, numbers and underscores.",
)


class RegisterSerializer(serializers.Serializer):
    """Validate and create a new user + profile.

    Enforces: well-formed email (unique), password >= 8 chars, and a username
    matching ^[a-zA-Z0-9_]+$ (unique).
    """

    username = serializers.CharField(
        min_length=3,
        max_length=150,
        validators=[USERNAME_VALIDATOR],
    )
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True, trim_whitespace=False)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists")
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
        )
        UserProfile.objects.get_or_create(user=user)
        return user


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
                    # Build absolute URL - ensures host:port are included
                    scheme = request.scheme
                    host = request.get_host()  # Gets host with port
                    path = obj.avatar.url
                    return f"{scheme}://{host}{path}"
                # Fallback if no request context
                from django.conf import settings
                backend_url = getattr(settings, 'BACKEND_URL', 'http://localhost:8000')
                return f"{backend_url}{obj.avatar.url}"
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
