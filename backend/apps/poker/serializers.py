"""Serializadores del historial de póker."""
from rest_framework import serializers

from .models import PokerHandPlayer, PokerHandRecord


class PokerHandPlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = PokerHandPlayer
        fields = ['seat', 'name', 'is_bot', 'hole', 'hand_name', 'stack_after', 'won', 'folded']


class PokerHandSerializer(serializers.ModelSerializer):
    players = PokerHandPlayerSerializer(many=True, read_only=True)

    class Meta:
        model = PokerHandRecord
        fields = ['id', 'hand_number', 'board', 'pot', 'showdown', 'winner_names',
                  'created_at', 'players']


class PokerHandReplaySerializer(serializers.ModelSerializer):
    """Una mano con su registro de acciones, para reproducirla paso a paso.

    Va aparte del serializador de la lista porque el registro pesa: una partida
    larga puede tener decenas de manos y no se necesita hasta que alguien abre una.
    """

    players = PokerHandPlayerSerializer(many=True, read_only=True)
    actions = serializers.JSONField()

    class Meta:
        model = PokerHandRecord
        fields = ['id', 'hand_number', 'board', 'pot', 'showdown', 'winner_names',
                  'created_at', 'players', 'actions']
