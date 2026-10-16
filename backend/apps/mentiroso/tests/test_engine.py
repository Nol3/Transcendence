"""Tests del motor del Mentiroso.

Son los mismos casos que los del motor del front (`mentiroso-engine.spec.ts`), a propósito: las
reglas están escritas dos veces —una para jugar en local y otra para el servidor— y la única
forma de que no se separen es que las dos se prueben con los mismos casos.
"""
from __future__ import annotations

import random
import unittest

from apps.baraja import SUITS
from apps.mentiroso.engine import (
    MANOS_POR_DEFECTO,
    MentirosoError,
    MentirosoState,
    desconfiar,
    new_game,
    next_hand,
    play,
    retirar,
    state_for,
)


def partida(n: int = 4, seed: int = 7) -> MentirosoState:
    return new_game(
        names=[f"J{i + 1}" for i in range(n)],
        bots=[i != 0 for i in range(n)],
        rng=random.Random(seed),
    )


def carta(state: MentirosoState, jugador: int, i: int = 0):
    return state.players[jugador].hand[i]


class RepartoTests(unittest.TestCase):
    def test_reparte_las_40_cartas_sin_perder_ninguna(self):
        s = partida(4)
        total = sum(len(p.hand) for p in s.players)
        self.assertEqual(total, 40)
        self.assertEqual(len({c.id for p in s.players for c in p.hand}), 40)

    def test_con_seis_jugadores_no_salen_iguales(self):
        s = partida(6)
        totales = [len(p.hand) for p in s.players]
        self.assertEqual(sum(totales), 40)
        self.assertLessEqual(max(totales) - min(totales), 1)

    def test_no_se_puede_jugar_fuera_de_turno(self):
        s = partida(4)
        with self.assertRaises(MentirosoError) as ctx:
            play(s, 1, [carta(s, 1).id], 5)
        self.assertEqual(ctx.exception.code, "not_your_turn")

    def test_no_se_puede_jugar_una_carta_que_no_es_tuya(self):
        s = partida(4)
        with self.assertRaises(MentirosoError) as ctx:
            play(s, 0, [carta(s, 1).id], 5)
        self.assertEqual(ctx.exception.code, "not_your_card")

    def test_el_que_abre_fija_el_valor_y_los_demas_no_lo_cambian(self):
        s = partida(4)
        play(s, 0, [carta(s, 0).id], 5)
        self.assertEqual(s.claimed_rank, 5)
        with self.assertRaises(MentirosoError) as ctx:
            play(s, 1, [carta(s, 1).id], 7)
        self.assertEqual(ctx.exception.code, "rank_changed")

    def test_no_se_puede_abrir_sin_decir_que_cartas_son(self):
        s = partida(4)
        with self.assertRaises(MentirosoError) as ctx:
            play(s, 0, [carta(s, 0).id])
        self.assertEqual(ctx.exception.code, "no_rank")

    def test_hacen_falta_entre_tres_y_seis_jugadores(self):
        for n in (2, 7):
            with self.assertRaises(MentirosoError):
                new_game(names=[f"J{i}" for i in range(n)])


class CantidadTests(unittest.TestCase):
    def test_la_cantidad_anunciada_es_la_que_se_pone(self):
        s = partida(4)
        cartas = [c.id for c in s.players[0].hand[:3]]
        play(s, 0, cartas, 5)
        self.assertEqual(s.events[-1], {"kind": "play", "player": 0, "count": 3, "claimedRank": 5})
        self.assertEqual(len(s.pile), 3)

    def test_si_se_puede_mentir_en_el_valor(self):
        s = partida(4)
        mentirosa = next(c for c in s.players[0].hand if c.rank != 5)
        play(s, 0, [mentirosa.id], 5)
        self.assertEqual(s.last_play.claimed_rank, 5)
        self.assertNotEqual(s.last_play.cards[0].rank, 5)


class DesconfiarTests(unittest.TestCase):
    def test_puede_desconfiar_cualquiera_no_solo_el_siguiente(self):
        s = partida(4)
        mentirosa = next(c for c in s.players[0].hand if c.rank != 5)
        play(s, 0, [mentirosa.id], 5)
        desconfiar(s, 3)  # el siguiente sería el 1
        self.assertTrue(any(e["kind"] == "challenge" and e["player"] == 3 for e in s.events))

    def test_si_mentia_se_lleva_el_monton_el_que_puso(self):
        s = partida(4)
        antes = len(s.players[0].hand)
        mentirosa = next(c for c in s.players[0].hand if c.rank != 5)
        play(s, 0, [mentirosa.id], 5)
        desconfiar(s, 1)
        self.assertEqual(len(s.pile), 0)
        self.assertEqual(len(s.players[0].hand), antes)
        self.assertEqual(s.events[-1]["kind"], "take")
        self.assertTrue(s.events[-1]["mentira"])
        self.assertEqual(s.events[-1]["player"], 0)

    def test_si_decia_la_verdad_se_lleva_el_monton_el_que_desconfio(self):
        s = partida(4)
        suya = s.players[0].hand[0]
        play(s, 0, [suya.id], suya.rank)
        desconfiar(s, 2)
        self.assertTrue(any(c.id == suya.id for c in s.players[2].hand))
        self.assertFalse(s.events[-1]["mentira"])
        self.assertEqual(s.events[-1]["player"], 2)

    def test_quien_se_lleva_el_monton_abre_la_ronda_con_valor_libre(self):
        s = partida(4)
        mentirosa = next(c for c in s.players[0].hand if c.rank != 5)
        play(s, 0, [mentirosa.id], 5)
        desconfiar(s, 1)
        self.assertEqual(s.turn, 0)
        self.assertIsNone(s.claimed_rank)

    def test_no_se_puede_desconfiar_si_no_hay_nada_puesto(self):
        s = partida(4)
        with self.assertRaises(MentirosoError) as ctx:
            desconfiar(s, 1)
        self.assertEqual(ctx.exception.code, "nothing_to_challenge")

    def test_no_te_puedes_desconfiar_a_ti_mismo(self):
        s = partida(4)
        play(s, 0, [carta(s, 0).id], 5)
        with self.assertRaises(MentirosoError) as ctx:
            desconfiar(s, 0)
        self.assertEqual(ctx.exception.code, "self_challenge")

    def test_a_quien_se_queda_sin_cartas_no_se_le_puede_desconfiar(self):
        s = partida(3)
        todas = [c.id for c in s.players[0].hand]
        play(s, 0, todas, 5)
        self.assertEqual(s.phase, "hand-end")  # se descarga entero y gana la mano
        with self.assertRaises(MentirosoError):
            desconfiar(s, 1)


class RetirarTests(unittest.TestCase):
    def _dar_cuatro_iguales(self, s: MentirosoState, jugador: int) -> int:
        valor = s.players[jugador].hand[0].rank
        cuatro = [c for c in s.players[jugador].hand if c.rank == valor][:4]
        # Completa hasta cuatro con cartas del mismo valor (una por palo).
        from apps.baraja import Card

        cuatro = [Card(rank=valor, suit=suit) for suit in SUITS]
        s.players[jugador].hand = cuatro + s.players[jugador].hand[4:]
        return valor

    def test_retira_las_cuatro_cartas_y_las_saca_del_juego(self):
        s = partida(4)
        valor = self._dar_cuatro_iguales(s, 0)
        antes = len(s.players[0].hand)
        retirar(s, 0, valor)
        self.assertEqual(len(s.players[0].hand), antes - 4)
        self.assertEqual(len(s.players[0].retired), 4)
        self.assertEqual(s.events[-1], {"kind": "retire", "player": 0, "rank": valor})

    def test_no_se_puede_retirar_sin_tener_los_cuatro(self):
        s = partida(4)
        with self.assertRaises(MentirosoError) as ctx:
            retirar(s, 0, 5)
        self.assertEqual(ctx.exception.code, "not_four")

    def test_retirar_sin_ser_tu_turno_no_mueve_el_turno(self):
        s = partida(4)
        valor = self._dar_cuatro_iguales(s, 2)
        turno = s.turn
        retirar(s, 2, valor)
        self.assertEqual(s.turn, turno)


class PartidaTests(unittest.TestCase):
    def test_la_mano_la_gana_quien_se_queda_sin_cartas(self):
        s = partida(3)
        play(s, 0, [carta(s, 0).id], 5)
        play(s, 1, [c.id for c in s.players[1].hand], 5)
        self.assertEqual(s.phase, "hand-end")
        self.assertEqual(s.winner, 1)
        self.assertEqual(s.players[1].wins, 1)

    def test_la_partida_termina_al_llegar_a_las_manos_pactadas(self):
        s = partida(3)
        for mano in range(MANOS_POR_DEFECTO):
            if s.phase == "hand-end":
                next_hand(s, random.Random(mano + 3))
            play(s, 0, [c.id for c in s.players[0].hand], 5)
            if s.phase == "hand-end" and mano < MANOS_POR_DEFECTO - 1:
                next_hand(s, random.Random(mano + 10))
        self.assertEqual(s.players[0].wins, MANOS_POR_DEFECTO)
        self.assertEqual(s.phase, "match-end")

    def test_no_se_reparte_la_mano_siguiente_si_la_anterior_sigue_viva(self):
        s = partida(3)
        with self.assertRaises(MentirosoError) as ctx:
            next_hand(s)
        self.assertEqual(ctx.exception.code, "not_finished")

    def test_una_partida_entera_con_bots_termina_y_no_pierde_cartas(self):
        s = partida(4, seed=99)
        vueltas = 0
        while s.phase != "match-end" and vueltas < 4000:
            vueltas += 1
            if s.phase == "hand-end":
                next_hand(s, random.Random(vueltas))
                continue
            yo = s.players[s.turn]
            valor = s.claimed_rank if s.claimed_rank is not None else yo.hand[0].rank
            carta_elegida = next((c for c in yo.hand if c.rank == valor), yo.hand[0])
            play(s, s.turn, [carta_elegida.id], valor)
        self.assertEqual(s.phase, "match-end")
        self.assertLess(vueltas, 4000)

        total = sum(len(p.hand) + len(p.retired) for p in s.players) + len(s.pile)
        self.assertEqual(total, 40)


class VistaTests(unittest.TestCase):
    def test_la_vista_trae_tu_mano_y_de_los_demas_solo_el_numero(self):
        s = partida(4)
        vista = state_for(s, 1)
        self.assertEqual(len(vista["myHand"]), len(s.players[1].hand))
        self.assertIn("suit", vista["myHand"][0])
        self.assertNotIn("hand", vista["players"][0])
        self.assertEqual(vista["players"][0]["handCount"], len(s.players[0].hand))

    def test_el_monton_nunca_se_revela(self):
        s = partida(4)
        play(s, 0, [carta(s, 0).id], 5)
        vista = state_for(s, 2)
        self.assertEqual(vista["pileCount"], 1)
        self.assertNotIn("pile", vista)
        self.assertNotIn("cards", str(vista))


if __name__ == "__main__":
    unittest.main()
