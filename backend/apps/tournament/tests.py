"""Tests for tournament bracket generation and progression.

Covers the core of `apps.tournament.services`:
- bracket seeding with a power-of-two field (4 players → 2 matches),
- byes for odd fields (lone player auto-advances),
- round progression via `report_match_result` up to crowning a winner,
- idempotency / guard rails.
"""
from django.contrib.auth.models import User
from django.test import TestCase

from apps.tournament.models import (
    Tournament,
    TournamentMatch,
    TournamentParticipant,
)
from apps.tournament.services import generate_bracket, report_match_result


def _make_tournament(creator, max_players):
    return Tournament.objects.create(
        name="Test Cup", creator=creator, max_players=max_players
    )


def _add_players(tournament, users):
    for u in users:
        TournamentParticipant.objects.create(tournament=tournament, user=u)


class BracketGenerationTests(TestCase):
    def setUp(self):
        self.users = [
            User.objects.create_user(username=f"p{i}", password="x") for i in range(4)
        ]

    def test_generate_bracket_with_four_players(self):
        """A full 4-player tournament seeds round 1 with two matches."""
        t = _make_tournament(self.users[0], max_players=4)
        _add_players(t, self.users)

        self.assertTrue(generate_bracket(t))

        t.refresh_from_db()
        self.assertEqual(t.status, "in_progress")
        self.assertIsNotNone(t.started_at)

        round1 = t.rounds.get(number=1)
        self.assertEqual(round1.name, "Semifinals")
        matches = list(round1.matches.order_by("position"))
        self.assertEqual(len(matches), 2)
        # Every participant is seeded into exactly one slot.
        seeded = {m.player1_id for m in matches} | {m.player2_id for m in matches}
        self.assertEqual(seeded, {u.id for u in self.users})

    def test_generate_bracket_not_full_is_noop(self):
        """Bracket is not generated while the tournament is under capacity."""
        t = _make_tournament(self.users[0], max_players=4)
        _add_players(t, self.users[:3])  # only 3 of 4

        self.assertFalse(generate_bracket(t))
        self.assertFalse(t.rounds.exists())

    def test_generate_bracket_is_idempotent(self):
        """Calling generate twice does not create a second round 1."""
        t = _make_tournament(self.users[0], max_players=4)
        _add_players(t, self.users)

        self.assertTrue(generate_bracket(t))
        self.assertFalse(generate_bracket(t))  # second call is a no-op
        self.assertEqual(t.rounds.filter(number=1).count(), 1)


class ByeTests(TestCase):
    def test_odd_field_creates_a_bye_that_auto_advances(self):
        """With 3 players, the lone player gets a completed bye match."""
        users = [User.objects.create_user(username=f"o{i}", password="x") for i in range(3)]
        t = _make_tournament(users[0], max_players=3)
        _add_players(t, users)

        self.assertTrue(generate_bracket(t))

        round1 = t.rounds.get(number=1)
        bye = round1.matches.filter(player2__isnull=True).first()
        self.assertIsNotNone(bye)
        self.assertEqual(bye.status, "completed")
        self.assertEqual(bye.winner_id, bye.player1_id)


class ProgressionTests(TestCase):
    def setUp(self):
        self.users = [
            User.objects.create_user(username=f"u{i}", password="x") for i in range(4)
        ]
        self.t = _make_tournament(self.users[0], max_players=4)
        _add_players(self.t, self.users)
        generate_bracket(self.t)

    def test_round_advances_only_when_all_matches_done(self):
        """Reporting one of two semis must NOT yet create the final."""
        semis = list(self.t.rounds.get(number=1).matches.order_by("position"))
        report_match_result(semis[0], winner_slot=1, player1_score=300, player2_score=120)

        self.t.refresh_from_db()
        self.assertFalse(self.t.rounds.filter(number=2).exists())
        self.assertEqual(self.t.status, "in_progress")

    def test_full_progression_crowns_a_winner(self):
        """Reporting both semis builds the final; reporting it finishes the cup."""
        semis = list(self.t.rounds.get(number=1).matches.order_by("position"))
        s0 = report_match_result(semis[0], winner_slot=1, player1_score=300, player2_score=100)
        s1 = report_match_result(semis[1], winner_slot=2, player1_score=90, player2_score=300)

        # Final round now exists with a single match between the two winners.
        final_round = self.t.rounds.get(number=2)
        self.assertEqual(final_round.name, "Final")
        final = final_round.matches.get()
        finalists = {final.player1_id, final.player2_id}
        self.assertEqual(finalists, {s0.winner_id, s1.winner_id})

        report_match_result(final, winner_slot=1)

        self.t.refresh_from_db()
        self.assertEqual(self.t.status, "finished")
        self.assertIsNotNone(self.t.finished_at)
        self.assertEqual(self.t.winner_id, final.player1_id)

    def test_loser_is_marked_eliminated(self):
        semis = list(self.t.rounds.get(number=1).matches.order_by("position"))
        match = semis[0]
        report_match_result(match, winner_slot=1)

        loser = match.player2
        participant = TournamentParticipant.objects.get(tournament=self.t, user=loser)
        self.assertTrue(participant.is_eliminated)

    def test_reporting_completed_match_is_ignored(self):
        """A second report on the same match does not flip the recorded winner."""
        match = self.t.rounds.get(number=1).matches.order_by("position")[0]
        report_match_result(match, winner_slot=1, player1_score=300, player2_score=10)
        first_winner = TournamentMatch.objects.get(pk=match.pk).winner_id

        report_match_result(match, winner_slot=2, player1_score=10, player2_score=300)
        self.assertEqual(TournamentMatch.objects.get(pk=match.pk).winner_id, first_winner)
