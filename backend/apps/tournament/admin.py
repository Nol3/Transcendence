"""Tournament app admin."""
from django.contrib import admin
from .models import Tournament, TournamentParticipant


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ['name', 'creator', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'creator__username']


@admin.register(TournamentParticipant)
class TournamentParticipantAdmin(admin.ModelAdmin):
    list_display = ['tournament', 'user', 'joined_at']
    list_filter = ['tournament', 'joined_at']
    search_fields = ['tournament__name', 'user__username']
