"""El resultado de una partida online lo escribe el SERVIDOR (no el navegador).

Comprueba que:
- humano vs humano queda en el historial y actualiza ELO y balance,
- humano vs bot queda en el historial pero **no** puntúa (no se infla el ranking).
"""
from __future__ import annotations

import asyncio

from django.contrib.auth.models import User
from django.test import TestCase, TransactionTestCase

from apps.games.models import Game
from apps.poker.services import _report_sync
from apps.poker.tables import PokerTable, TableSeat
from apps.users.models import UserProfile


def make_table(seats, winner_index=0, stacks=(2000, 0)):
    table = PokerTable("test", seats, small_blind=5, big_blind=10)
    for seat, stack in zip(table.seats, stacks, strict=False):
        seat.stack = stack
    table.winner = table.seats[winner_index]
    table.finished = True
    return table


class ReportMatchEndTests(TestCase):
    def setUp(self):
        self.p1 = User.objects.create_user("ana", "ana@example.com", "Zx9!pqLmn42")
        self.p2 = User.objects.create_user("luis", "luis@example.com", "Zx9!pqLmn42")
        UserProfile.objects.get_or_create(user=self.p1)
        UserProfile.objects.get_or_create(user=self.p2)

    def test_humano_vs_humano_puntua(self):
        table = make_table([
            TableSeat(index=0, user_id=self.p1.id, username="ana", stack=2000),
            TableSeat(index=1, user_id=self.p2.id, username="luis", stack=2000),
        ])
        _report_sync(table)

        game = Game.objects.latest("id")
        self.assertEqual(game.status, "finished")
        self.assertEqual(game.winner, self.p1)
        self.assertEqual(game.player1, self.p1)
        self.assertEqual(game.player2, self.p2)

        self.p1.profile.refresh_from_db()
        self.p2.profile.refresh_from_db()
        self.assertEqual(self.p1.profile.win_count, 1)
        self.assertEqual(self.p2.profile.loss_count, 1)
        self.assertGreater(self.p1.profile.elo_rating, 1600)
        self.assertLess(self.p2.profile.elo_rating, 1600)

    def test_partida_contra_bot_no_puntua(self):
        table = make_table([
            TableSeat(index=0, user_id=self.p1.id, username="ana", stack=2000),
            TableSeat(index=1, username="Bot Málaga", stack=2000, is_bot=True),
        ])
        _report_sync(table)

        game = Game.objects.latest("id")
        self.assertEqual(game.status, "finished")
        self.assertEqual(game.winner, self.p1)
        self.assertEqual(game.player2.username, "AI_Opponent")   # cuenta interna del bot

        self.p1.profile.refresh_from_db()
        self.assertEqual(self.p1.profile.win_count, 0, "ganar a un bot no debe contar como victoria")
        self.assertEqual(self.p1.profile.elo_rating, 1600, "ganar a un bot no debe subir el ELO")

    def test_empate_no_da_ganador(self):  # noqa: D102
        table = make_table([
            TableSeat(index=0, user_id=self.p1.id, username="ana", stack=1000),
            TableSeat(index=1, user_id=self.p2.id, username="luis", stack=1000),
        ], winner_index=0, stacks=(1000, 1000))
        table.winner = None                                     # empate real
        _report_sync(table)

        game = Game.objects.latest("id")
        self.assertIsNone(game.winner)
        self.p1.profile.refresh_from_db()
        self.p2.profile.refresh_from_db()
        self.assertEqual(self.p1.profile.win_count, 0)
        self.assertEqual(self.p2.profile.loss_count, 0)




class AsyncHookTests(TransactionTestCase):
    """El hook que usa la mesa corre en otro hilo: necesita datos confirmados."""

    def test_el_hook_asincrono_registra_el_resultado(self):
        from apps.poker.services import report_match_end

        p1 = User.objects.create_user("hook1", "hook1@example.com", "Zx9!pqLmn42")
        p2 = User.objects.create_user("hook2", "hook2@example.com", "Zx9!pqLmn42")
        UserProfile.objects.get_or_create(user=p1)
        UserProfile.objects.get_or_create(user=p2)
        table = make_table([
            TableSeat(index=0, user_id=p1.id, username="hook1", stack=2000),
            TableSeat(index=1, user_id=p2.id, username="hook2", stack=2000),
        ])
        asyncio.run(report_match_end(table))
        self.assertEqual(Game.objects.filter(status="finished").count(), 1)
