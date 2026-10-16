"""Modelos de la app de póker: historial de manos y jugadores de cada mano.

El motor ya produce un resumen completo al acabar cada mano (`Hand.result`); esto
lo guarda para que el jugador pueda revisar qué pasó, en vez de perderlo al cerrar
la mesa (hasta ahora solo quedaba una fila `Game` por partida).
"""
from __future__ import annotations

from django.contrib.auth.models import User
from django.db import models


class PokerPreference(models.Model):
    """Preferencias del jugador para el póker online (módulo «game customization»).

    Hoy el módulo de customización solo aplicaba al juego local; esto lleva al póker
    online el tema del tapete, el nivel de ciegas y el tamaño de mesa por defecto, y
    los guarda por usuario.
    """

    THEMES = [
        ('classic', 'Classic'),
        ('neon', 'Neon'),
        ('crimson', 'Crimson'),
        ('violet', 'Violet'),
        ('gold', 'Gold'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='poker_preference')
    theme = models.CharField(max_length=16, choices=THEMES, default='classic')
    stake = models.CharField(max_length=8, default='low', help_text='micro | low | mid')
    table_size = models.PositiveSmallIntegerField(default=2, help_text='2–6 asientos')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Poker preference'
        verbose_name_plural = 'Poker preferences'

    def __str__(self):
        return f'Preferencias de póker de {self.user.username} ({self.theme})'


class PokerHandRecord(models.Model):
    """Una mano jugada en una mesa."""

    # Partida (fila `Game`) a la que pertenece la mano. Puede ser NULL si la mano
    # se guardó sin partida asociada.
    game = models.ForeignKey(
        'games.Game', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='poker_hands',
    )
    table_id = models.CharField(max_length=32)
    hand_number = models.PositiveIntegerField()
    board = models.CharField(
        max_length=32, blank=True,
        help_text='Comunitarias, p. ej. "7c 2s Ad Td 9d"',
    )
    pot = models.PositiveIntegerField(default=0)
    showdown = models.BooleanField(default=False)
    # Se desnormaliza para poder listar el historial sin recorrer los jugadores.
    winner_names = models.CharField(max_length=200, blank=True)
    # Registro de acciones de la mano (ciegas, apuestas, calles, resultado), tal cual
    # lo emite el motor. Permite reproducir la mano paso a paso (roadmap 7.2). Las
    # manos antiguas se quedan con la lista vacía.
    actions = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Poker hand'
        verbose_name_plural = 'Poker hands'
        ordering = ['-created_at', '-hand_number']
        indexes = [models.Index(fields=['game', 'hand_number'])]

    def __str__(self):
        return f'Mano #{self.hand_number} en {self.table_id} (bote {self.pot})'


class PokerHandPlayer(models.Model):
    """Participación de un asiento en una mano (incluye bots)."""

    hand = models.ForeignKey(PokerHandRecord, related_name='players', on_delete=models.CASCADE)
    # NULL en los bots: no son usuarios del sistema.
    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='poker_hands_played',
    )
    seat = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=50)
    is_bot = models.BooleanField(default=False)
    # Cartas solo si se mostraron (showdown); si no, van vacías.
    hole = models.CharField(max_length=16, blank=True)
    hand_name = models.CharField(max_length=40, blank=True)
    stack_after = models.IntegerField(default=0)
    won = models.IntegerField(default=0)
    folded = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Poker hand player'
        verbose_name_plural = 'Poker hand players'
        ordering = ['seat']

    def __str__(self):
        return f'{self.name} (asiento {self.seat}) en mano #{self.hand_id}'
