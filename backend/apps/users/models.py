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
    # Racha de días entrando (distinta de la racha de victorias que se calcula sobre las partidas).
    # Se guarda la fecha del último check-in, no un contador que haya que resetear por cron.
    login_streak = models.PositiveIntegerField(default=0)
    best_login_streak = models.PositiveIntegerField(default=0)
    last_checkin = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f"{self.user.username} Profile"
