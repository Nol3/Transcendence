"""Games app models."""
from django.db import models
from django.contrib.auth.models import User


class Game(models.Model):
    """Game record."""
    GAME_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('finished', 'Finished'),
    ]

    player1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='games_as_player1')
    player2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='games_as_player2')
    winner = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='games_won')
    status = models.CharField(max_length=20, choices=GAME_STATUS_CHOICES, default='pending')
    player1_score = models.IntegerField(default=0)
    player2_score = models.IntegerField(default=0)
    played_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Game'
        verbose_name_plural = 'Games'
        ordering = ['-played_at']

    def __str__(self):
        return f"{self.player1.username} vs {self.player2.username}"
