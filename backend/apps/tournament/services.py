"""Tournament bracket generation and progression logic.

Single-elimination bracket. Rounds are created lazily: round N+1 is built only
once every match in round N is completed, so the bracket grows as results come
in. Odd player counts are handled with byes (player2 = None auto-advances).
"""
from __future__ import annotations

import math
import random

from django.db import transaction
from django.utils import timezone

from .models import Tournament, TournamentMatch, TournamentRound

# Human-friendly names for the last rounds of a bracket, keyed by how many
# matches the round contains.
_ROUND_NAMES_BY_MATCH_COUNT = {
    1: 'Final',
    2: 'Semifinals',
    4: 'Quarterfinals',
}


def _round_name(number: int, match_count: int) -> str:
    return _ROUND_NAMES_BY_MATCH_COUNT.get(match_count, f'Round {number}')


def _broadcast(tournament: Tournament) -> None:
    """Push the fresh tournament state to WebSocket subscribers (best effort).

    Imported lazily and guarded so the REST flow keeps working even when the
    channel layer is not configured (e.g. running under plain WSGI).
    """
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        from .serializers import TournamentSerializer

        layer = get_channel_layer()
        if layer is None:
            return
        data = TournamentSerializer(tournament).data
        async_to_sync(layer.group_send)(
            f'tournament_{tournament.id}',
            {'type': 'tournament_update', 'tournament': data},
        )
    except Exception:
        # Real-time updates are an enhancement, never a hard dependency.
        pass


@transaction.atomic
def generate_bracket(tournament: Tournament) -> bool:
    """Seed round 1 when the tournament is full. Returns True if it generated.

    Idempotent: does nothing if a bracket already exists or the tournament is
    not full yet.
    """
    if tournament.rounds.exists():
        return False

    participants = list(tournament.participants.select_related('user').all())
    if len(participants) < 2 or len(participants) < tournament.max_players:
        return False

    players = [p.user for p in participants]
    random.shuffle(players)

    match_count = math.ceil(len(players) / 2)
    first_round = TournamentRound.objects.create(
        tournament=tournament,
        number=1,
        name=_round_name(1, match_count),
    )

    position = 0
    for i in range(0, len(players), 2):
        p1 = players[i]
        p2 = players[i + 1] if i + 1 < len(players) else None
        match = TournamentMatch.objects.create(
            tournament=tournament,
            round=first_round,
            position=position,
            player1=p1,
            player2=p2,
            status='pending',
        )
        # Lone player → automatic bye, immediately advance.
        if p2 is None:
            match.winner = p1
            match.status = 'completed'
            match.finished_at = timezone.now()
            match.save(update_fields=['winner', 'status', 'finished_at'])
        position += 1

    tournament.status = 'in_progress'
    tournament.started_at = timezone.now()
    tournament.save(update_fields=['status', 'started_at'])

    _maybe_advance_round(tournament, first_round)
    _broadcast(tournament)
    return True


@transaction.atomic
def report_match_result(
    match: TournamentMatch,
    winner_slot: int,
    player1_score: int = 0,
    player2_score: int = 0,
) -> TournamentMatch:
    """Record a match result and advance the bracket if the round is done."""
    if match.status == 'completed':
        return match

    match.player1_score = player1_score
    match.player2_score = player2_score
    match.winner = match.player1 if winner_slot == 1 else match.player2
    match.status = 'completed'
    match.finished_at = timezone.now()
    match.save(update_fields=[
        'player1_score', 'player2_score', 'winner', 'status', 'finished_at',
    ])

    loser = match.player2 if winner_slot == 1 else match.player1
    if loser is not None:
        match.tournament.participants.filter(user=loser).update(is_eliminated=True)

    _maybe_advance_round(match.tournament, match.round)
    _broadcast(match.tournament)
    return match


def _maybe_advance_round(tournament: Tournament, current_round: TournamentRound) -> None:
    """If every match in `current_round` is done, build the next round or finish."""
    matches = list(current_round.matches.order_by('position'))
    if not matches or any(m.status != 'completed' for m in matches):
        return

    winners = [m.winner for m in matches if m.winner is not None]

    # Tournament is decided.
    if len(winners) <= 1:
        tournament.status = 'finished'
        tournament.finished_at = timezone.now()
        tournament.winner = winners[0] if winners else None
        tournament.save(update_fields=['status', 'finished_at', 'winner'])
        return

    next_number = current_round.number + 1
    if tournament.rounds.filter(number=next_number).exists():
        return

    match_count = math.ceil(len(winners) / 2)
    next_round = TournamentRound.objects.create(
        tournament=tournament,
        number=next_number,
        name=_round_name(next_number, match_count),
    )

    position = 0
    for i in range(0, len(winners), 2):
        p1 = winners[i]
        p2 = winners[i + 1] if i + 1 < len(winners) else None
        match = TournamentMatch.objects.create(
            tournament=tournament,
            round=next_round,
            position=position,
            player1=p1,
            player2=p2,
            status='pending',
        )
        if p2 is None:
            match.winner = p1
            match.status = 'completed'
            match.finished_at = timezone.now()
            match.save(update_fields=['winner', 'status', 'finished_at'])
        position += 1

    # A round full of byes can cascade into the next round immediately.
    _maybe_advance_round(tournament, next_round)
