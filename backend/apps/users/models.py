"""Users app models."""
from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    """Extended user profile."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', default='default_avatar.jpg')
    win_count = models.IntegerField(default=0)
    loss_count = models.IntegerField(default=0)
    # Con índice: el ranking ordena **todos** los perfiles por este campo y el perfil propio
    # cuenta cuántos van por delante, así que se recorre entero en cada consulta.
    elo_rating = models.FloatField(default=1600, db_index=True)
    is_online = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f"{self.user.username} Profile"
