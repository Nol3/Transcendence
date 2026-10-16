"""Games app models."""
from django.contrib.auth.models import User
from django.db import models


class Game(models.Model):
    """Game record."""
    GAME_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('finished', 'Finished'),
    ]

    player1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='games_as_player1')
    player2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='games_as_player2')
    winner = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name='games_won'
    )
    status = models.CharField(max_length=20, choices=GAME_STATUS_CHOICES, default='pending')
    player1_score = models.IntegerField(default=0)
    player2_score = models.IntegerField(default=0)
    # Una partida es puntuable solo si el resultado lo ha decidido el servidor.
    # Las del modo local (WASM/hotseat) las reporta el navegador, así que no
    # pueden mover el ELO: si no, cualquiera se fabrica victorias.
    rated = models.BooleanField(
        default=True,
        help_text="Si es False, el resultado se guarda en el historial pero no "
                  "afecta al ELO ni al balance de victorias/derrotas.",
    )
    played_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Game'
        verbose_name_plural = 'Games'
        ordering = ['-played_at']
        # El historial filtra por estado y ordena por fecha de fin: con el índice se resuelven
        # las dos cosas sin recorrer la tabla entera. (Los jugadores ya van indexados solos por
        # ser claves ajenas.)
        indexes = [
            models.Index(fields=['status', 'finished_at'], name='game_status_finished_idx'),
        ]

    def __str__(self):
        return f"{self.player1.username} vs {self.player2.username}"
