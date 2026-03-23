"""Tournament app serializers."""
from rest_framework import serializers
from .models import Tournament, TournamentParticipant
from apps.users.serializers import UserSerializer


class TournamentParticipantSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = TournamentParticipant
        fields = ['id', 'user', 'joined_at']


class TournamentSerializer(serializers.ModelSerializer):
    creator = UserSerializer(read_only=True)
    participants = TournamentParticipantSerializer(many=True, read_only=True)

    class Meta:
        model = Tournament
        fields = ['id', 'name', 'description', 'creator', 'max_players', 'status', 'created_at', 'started_at', 'finished_at', 'participants']
