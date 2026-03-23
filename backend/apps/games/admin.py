"""Games app admin."""
from django.contrib import admin
from .models import Game


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ['player1', 'player2', 'winner', 'status', 'played_at']
    list_filter = ['status', 'played_at']
    search_fields = ['player1__username', 'player2__username', 'winner__username']
