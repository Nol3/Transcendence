"""Users app models."""
from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    """Extended user profile."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', default='default_avatar.jpg')
    win_count = models.IntegerField(default=0)
    loss_count = models.IntegerField(default=0)
    elo_rating = models.FloatField(default=1600)
    is_online = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f"{self.user.username} Profile"
