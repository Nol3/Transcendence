"""Tournament app models."""
from django.db import models
from django.contrib.auth.models import User


class Tournament(models.Model):
    """Tournament."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('finished', 'Finished'),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_tournaments')
    max_players = models.IntegerField(default=8)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    winner = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='tournaments_won',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Tournament'
        verbose_name_plural = 'Tournaments'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class TournamentParticipant(models.Model):
    """Tournament participant."""
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_eliminated = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('tournament', 'user')

    def __str__(self):
        return f"{self.user.username} in {self.tournament.name}"


class TournamentRound(models.Model):
    """A single round of a tournament bracket (e.g. Round 1, Semifinals)."""
    tournament = models.ForeignKey(
        Tournament, on_delete=models.CASCADE, related_name='rounds'
    )
    number = models.PositiveIntegerField()
    name = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Tournament Round'
        verbose_name_plural = 'Tournament Rounds'
        ordering = ['number']
        unique_together = ('tournament', 'number')

    def __str__(self):
        return f"{self.tournament.name} - {self.name}"


class TournamentMatch(models.Model):
    """A pairing inside a tournament round."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('live', 'Live'),
        ('completed', 'Completed'),
    ]

    tournament = models.ForeignKey(
        Tournament, on_delete=models.CASCADE, related_name='matches'
    )
    round = models.ForeignKey(
        TournamentRound, on_delete=models.CASCADE, related_name='matches'
    )
    position = models.PositiveIntegerField(default=0)
    player1 = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='tournament_matches_as_p1',
    )
    player2 = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='tournament_matches_as_p2',
    )
    winner = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='tournament_matches_won',
    )
    player1_score = models.IntegerField(default=0)
    player2_score = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Tournament Match'
        verbose_name_plural = 'Tournament Matches'
        ordering = ['round__number', 'position']

    def __str__(self):
        p1 = self.player1.username if self.player1 else 'TBD'
        p2 = self.player2.username if self.player2 else 'TBD'
        return f"R{self.round.number}#{self.position}: {p1} vs {p2}"
