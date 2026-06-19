"""Game result + ELO rating logic.

Standard Elo with K=32. A win/loss/draw updates both players' ratings and their
win/loss counters on the related UserProfile. The AI bot opponent is skipped so
it never pollutes the leaderboard.
"""
from __future__ import annotations

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

K_FACTOR = 32
AI_USERNAME = "AI_Opponent"


def get_ai_opponent() -> User:
    """Return (creating if needed) the singleton AI opponent user + profile."""
    from .models import Game  # noqa: F401  (ensures app is ready)
    from apps.users.models import UserProfile

    user, _ = User.objects.get_or_create(
        username=AI_USERNAME,
        defaults={"first_name": "AI", "last_name": "Opponent"},
    )
    UserProfile.objects.get_or_create(user=user)
    return user


def _expected(rating_a: float, rating_b: float) -> float:
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))


def _profile(user: User):
    from apps.users.models import UserProfile

    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


@transaction.atomic
def finish_game(game, winner: User | None, player1_score: int, player2_score: int):
    """Persist the result and update ELO/win/loss for both human players.

    `winner` is None for a draw. Idempotent: a game already marked finished is
    returned untouched so retried POSTs don't double-count stats.
    """
    if game.status == "finished":
        return game

    game.player1_score = player1_score
    game.player2_score = player2_score
    game.winner = winner
    game.status = "finished"
    game.finished_at = timezone.now()
    game.save(update_fields=[
        "player1_score", "player2_score", "winner", "status", "finished_at",
    ])

    p1, p2 = game.player1, game.player2
    prof1, prof2 = _profile(p1), _profile(p2)
    r1, r2 = prof1.elo_rating, prof2.elo_rating

    if winner is None:
        s1 = s2 = 0.5
    elif winner.id == p1.id:
        s1, s2 = 1.0, 0.0
    else:
        s1, s2 = 0.0, 1.0

    prof1.elo_rating = round(r1 + K_FACTOR * (s1 - _expected(r1, r2)), 2)
    prof2.elo_rating = round(r2 + K_FACTOR * (s2 - _expected(r2, r1)), 2)

    if winner is not None:
        if winner.id == p1.id:
            prof1.win_count += 1
            prof2.loss_count += 1
        else:
            prof2.win_count += 1
            prof1.loss_count += 1

    # Keep the AI bot out of the human leaderboard/stats.
    if p1.username != AI_USERNAME:
        prof1.save(update_fields=["elo_rating", "win_count", "loss_count"])
    if p2.username != AI_USERNAME:
        prof2.save(update_fields=["elo_rating", "win_count", "loss_count"])

    return game
