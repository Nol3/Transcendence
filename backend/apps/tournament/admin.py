"""Tournament app admin."""
from django.contrib import admin
from .models import (
    Tournament,
    TournamentParticipant,
    TournamentRound,
    TournamentMatch,
)


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ['name', 'creator', 'status', 'winner', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'creator__username']


@admin.register(TournamentParticipant)
class TournamentParticipantAdmin(admin.ModelAdmin):
    list_display = ['tournament', 'user', 'is_eliminated', 'joined_at']
    list_filter = ['tournament', 'is_eliminated', 'joined_at']
    search_fields = ['tournament__name', 'user__username']


@admin.register(TournamentRound)
class TournamentRoundAdmin(admin.ModelAdmin):
    list_display = ['tournament', 'number', 'name', 'created_at']
    list_filter = ['tournament']


@admin.register(TournamentMatch)
class TournamentMatchAdmin(admin.ModelAdmin):
    list_display = ['tournament', 'round', 'position', 'player1', 'player2', 'winner', 'status']
    list_filter = ['status', 'tournament']
