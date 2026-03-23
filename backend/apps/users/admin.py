"""Users app admin."""
from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'elo_rating', 'win_count', 'loss_count', 'is_online']
    list_filter = ['is_online', 'created_at']
    search_fields = ['user__username', 'user__email']
