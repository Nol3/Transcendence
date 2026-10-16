"""Bots y ciclo de vida de la mesa (turnos, inactividad, fin de partida)."""
from __future__ import annotations

import asyncio
import random

from django.test import SimpleTestCase

from apps.poker.bots import decide, preflop_strength
from apps.poker.engine import Hand
from apps.poker.tables import PokerTable, TableSeat


class BotTests(SimpleTestCase):
    def test_fuerza_preflop_ordena_las_manos_como_espera_el_poker(self):
        def power(text):
            from apps.poker.engine import parse_cards

            return preflop_strength(parse_cards(text))

        self.assertGreater(power("As Ad"), power("Ks Kd"))     # AA > KK
        self.assertGreater(power("Ks Kd"), power("7c 2h"))     # pareja > basura
        self.assertGreater(power("As Ks"), power("As 2d"))     # mismo palo y conectadas
        self.assertGreater(power("Ah Kh"), power("2c 3d"))

    def test_el_bot_siempre_elige_una_accion_legal(self):
        """Fuzz: 200 manos aleatorias jugadas por dos bots sin una sola acción ilegal."""
        rng = random.Random(20261012)
        for _ in range(200):
            hand = Hand(stacks=[200, 200], small_blind=1, big_blind=2, rng=rng).start()
            guard = 0
            while not hand.complete and guard < 200:
                guard += 1
                idx = hand.actor
                action, amount = decide(hand, idx, rng)
                hand.act(idx, action, amount)   # lanza IllegalAction si el bot falla
            self.assertTrue(hand.complete)
            self.assertEqual(sum(s.stack for s in hand.seats), 400)

    def test_motor_y_bot_conservan_las_fichas_en_mesas_de_2_a_6(self):
        rng = random.Random(99)
        for n_seats in (2, 3, 4, 6):
            with self.subTest(asientos=n_seats):
                stacks = [150] * n_seats
                hand = Hand(stacks=stacks, small_blind=1, big_blind=2, rng=rng).start()
                guard = 0
                while not hand.complete and guard < 400:
                    guard += 1
                    idx = hand.actor
                    action, amount = decide(hand, idx, rng)
                    hand.act(idx, action, amount)
                self.assertTrue(hand.complete)
                self.assertEqual(sum(s.stack for s in hand.seats), sum(stacks))


class TableTests(SimpleTestCase):
    def _table(self, **kwargs):
        seats = [
            TableSeat(index=0, user_id=1, username="Humano", stack=50),
            TableSeat(index=1, username="Bot", stack=50, is_bot=True),
        ]
        defaults = dict(small_blind=5, big_blind=10, turn_timeout=0.05,
                        bot_delay=0.001, next_hand_delay=0.02, rng=random.Random(3))
        defaults.update(kwargs)
        table = PokerTable("test-table", seats, **defaults)
        table.start()
        return table

    async def test_la_mesa_avanza_sola_y_termina(self):
        """El humano se conecta y se queda quieto: la mesa juega por él y cierra."""
        table = self._table(max_hands=4)
        try:
            await table.join("chan-humano", 1, "Humano")
            for _ in range(600):
                if table.finished:
                    break
                await asyncio.sleep(0.02)
            self.assertTrue(table.finished, "la partida debería cerrarse sola")
            self.assertEqual(sum(s.stack for s in table.seats), 100)
            stacks = sorted((s.stack for s in table.seats), reverse=True)
            if stacks[0] == stacks[1]:
                self.assertIsNone(table.winner, "un empate no debe declarar ganador")
            else:
                self.assertIsNotNone(table.winner)
            self.assertTrue(any(ev.get("event") == "timeout" for ev in table.log),
                            "el humano inactivo debe ser pasado/foldeado automáticamente")
        finally:
            table._cancel_tasks()

    async def test_el_bot_juega_sus_turnos_sin_ayuda(self):
        table = self._table(turn_timeout=5.0)
        try:
            await table.join("chan-humano", 1, "Humano")
            bot_actions = []
            for _ in range(400):
                hand = table.hand
                if hand is None:
                    await asyncio.sleep(0.02)
                    continue
                bot_actions = [ev for ev in hand.history
                               if ev.get("event") == "action" and ev.get("seat") == 1]
                if bot_actions:
                    break
                if hand.actor == 0 and not hand.complete:
                    opts = {o["action"]: o for o in hand.legal_actions(0)}
                    if "check" in opts:
                        await table.act(1, "check")
                    elif "call" in opts:
                        await table.act(1, "call", opts["call"]["amount"])
                    else:
                        await table.act(1, "fold")
                await asyncio.sleep(0.02)
            self.assertTrue(bot_actions, "el bot debería haber actuado por su cuenta")
        finally:
            table._cancel_tasks()

    async def test_snapshot_no_filtra_las_cartas_ajenas(self):
        table = self._table()
        try:
            await asyncio.sleep(0.05)
            view = table.snapshot(for_user_id=1)
            self.assertEqual(view["you"], 0)
            self.assertIsNotNone(view["game"]["seats"][0]["hole"])
            self.assertIsNone(view["game"]["seats"][1]["hole"])
            spectator = table.snapshot(for_user_id=None)
            self.assertTrue(all(s["hole"] is None for s in spectator["game"]["seats"]))
        finally:
            table._cancel_tasks()

    async def test_join_y_leave_de_un_asiento(self):
        table = self._table(turn_timeout=5.0)
        try:
            self.assertTrue(await table.join("chan-1", 1, "Humano"))
            self.assertTrue(table.seats[0].connected)
            await table.leave("chan-1")
            self.assertFalse(table.seats[0].connected)
            self.assertFalse(await table.join("chan-2", 999, "Intruso"),
                             "un usuario que no está sentado no puede entrar")
        finally:
            table._cancel_tasks()
