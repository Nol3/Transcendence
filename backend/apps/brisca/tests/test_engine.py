"""Tests del motor de la Brisca en el servidor.

Son los mismos casos que los del front (`brisca-engine.spec.ts`), a propósito: las reglas están
escritas dos veces —una para jugar en local y otra para el servidor— y la única forma de que no se
separen es probarlas con los mismos casos.
"""
from __future__ import annotations

import random
import unittest

from apps.baraja import Card
from apps.bazas import fuerza, ganador_de_baza, puntos, tantos
from apps.brisca.engine import (
    BriscaError,
    cambiar_triunfo,
    new_game,
    next_game,
    play,
    puede_cambiar_triunfo,
    state_for,
)


def carta(rank: int, suit: str) -> Card:
    return Card(rank=rank, suit=suit)


def partida(n: int = 2, seed: int = 7):
    return new_game(
        names=[f"J{i + 1}" for i in range(n)],
        bots=[i != 0 for i in range(n)],
        rng=random.Random(seed),
    )


class BazasTests(unittest.TestCase):
    def test_el_tres_va_por_delante_del_rey(self):
        # La trampa al copiar el orden del Culo.
        self.assertGreater(fuerza(carta(3, "o")), fuerza(carta(12, "o")))
        self.assertGreater(fuerza(carta(1, "o")), fuerza(carta(3, "o")))
        self.assertLess(fuerza(carta(2, "o")), fuerza(carta(4, "o")))

    def test_los_tantos_son_los_de_las_normas(self):
        self.assertEqual(puntos(carta(1, "o")), 11)
        self.assertEqual(puntos(carta(3, "c")), 10)
        self.assertEqual(puntos(carta(12, "e")), 4)
        self.assertEqual(puntos(carta(11, "b")), 3)
        self.assertEqual(puntos(carta(10, "o")), 2)
        self.assertEqual(puntos(carta(7, "o")), 0)
        self.assertEqual(tantos([carta(1, "o"), carta(3, "c"), carta(7, "e")]), 21)

    def test_gana_el_triunfo_mas_alto_aunque_salga_otro_palo(self):
        baza = [(0, carta(1, "o")), (1, carta(2, "c"))]
        self.assertEqual(ganador_de_baza(baza, "c"), 1)

    def test_sin_triunfo_gana_la_mas_alta_del_palo_de_salida(self):
        baza = [(0, carta(4, "o")), (1, carta(12, "c"))]
        self.assertEqual(ganador_de_baza(baza, "e"), 0)


class RepartoTests(unittest.TestCase):
    def test_tres_cartas_a_cada_uno_y_una_descubierta(self):
        s = partida(2)
        self.assertEqual([len(p.hand) for p in s.players], [3, 3])
        self.assertIsNotNone(s.trump_card)
        self.assertEqual(s.trump_suit, s.trump_card.suit)

    def test_no_se_pierde_ninguna_carta(self):
        s = partida(2)
        en_manos = sum(len(p.hand) for p in s.players)
        self.assertEqual(en_manos + len(s.deck) + (1 if s.trump_card else 0), 40)

    def test_no_se_juega_fuera_de_turno(self):
        s = partida(2)
        otro = (s.turn + 1) % 2
        with self.assertRaises(BriscaError) as ctx:
            play(s, otro, s.players[otro].hand[0].id)
        self.assertEqual(ctx.exception.code, "not_your_turn")

    def test_no_se_juega_una_carta_ajena(self):
        s = partida(2)
        ajeno = s.players[(s.turn + 1) % 2].hand[0].id
        with self.assertRaises(BriscaError) as ctx:
            play(s, s.turn, ajeno)
        self.assertEqual(ctx.exception.code, "not_your_card")

    def test_cualquier_carta_vale_no_hay_obligacion_de_asistir(self):
        # En la brisca no hay obligación de asistir: cualquiera de tus tres cartas es legal.
        for indice in range(3):
            s = partida(2)  # estado limpio para cada intento
            carta = s.players[s.turn].hand[indice]
            self.assertIsNone(play(s, s.turn, carta.id))
            self.assertEqual(s.trick[-1][1].id, carta.id)


class BazaTests(unittest.TestCase):
    def test_el_que_gana_se_lleva_las_cartas_roba_primero_y_sale(self):
        s = partida(2)
        quien = s.turn
        triunfo = next((c for c in s.players[quien].hand if c.suit == s.trump_suit), None)
        play(s, quien, (triunfo or s.players[quien].hand[0]).id)
        play(s, s.turn, s.players[s.turn].hand[0].id)

        self.assertEqual(s.trick, [])
        self.assertIsNotNone(s.last_trick)
        ganador = s.last_trick[0]
        self.assertEqual(len(s.players[ganador].won), 2)
        self.assertEqual(s.turn, ganador)
        self.assertEqual(len(s.players[ganador].hand), 3)

    def test_la_carta_que_pinta_es_la_ultima_que_se_roba(self):
        s = partida(2)
        vueltas = 0
        while s.trump_card is not None and vueltas < 100:
            vueltas += 1
            play(s, s.turn, s.players[s.turn].hand[0].id)
            play(s, s.turn, s.players[s.turn].hand[0].id)
        self.assertIsNone(s.trump_card)
        self.assertLess(vueltas, 100)

    def test_el_juego_termina_cuando_no_queda_nada(self):
        s = partida(2)
        vueltas = 0
        while s.phase == "playing" and vueltas < 200:
            vueltas += 1
            play(s, s.turn, s.players[s.turn].hand[0].id)
            if s.phase == "playing":
                play(s, s.turn, s.players[s.turn].hand[0].id)
        self.assertNotEqual(s.phase, "playing")
        self.assertTrue(all(not p.hand for p in s.players))
        self.assertEqual(sum(len(p.won) for p in s.players), 40)
        self.assertEqual(sum(s.scores), 120)


class CambioDeTriunfoTests(unittest.TestCase):
    def _tras_una_baza(self, seed=7):
        s = partida(2, seed)
        play(s, s.turn, s.players[s.turn].hand[0].id)
        play(s, s.turn, s.players[s.turn].hand[0].id)
        return s

    def test_solo_puede_cambiarlo_quien_gano_la_baza(self):
        s = self._tras_una_baza()
        perdedor = (s.last_winner + 1) % 2
        with self.assertRaises(BriscaError) as ctx:
            cambiar_triunfo(s, perdedor)
        self.assertEqual(ctx.exception.code, "not_your_trick")
        self.assertFalse(puede_cambiar_triunfo(s, perdedor))

    def test_con_el_siete_en_la_mano_se_queda_con_la_que_pintaba(self):
        s = self._tras_una_baza()
        ganador = s.last_winner
        pintaba = s.trump_card
        siete = Card(rank=7, suit=pintaba.suit, copy=9)
        s.players[ganador].hand.append(siete)

        cambiar_triunfo(s, ganador)
        self.assertEqual(s.trump_card.id, siete.id)
        self.assertTrue(any(c.id == pintaba.id for c in s.players[ganador].hand))
        self.assertEqual(s.events[-1], {"kind": "swap", "player": ganador, "card": siete.id})

    def test_sin_el_siete_no_hay_cambio(self):
        s = self._tras_una_baza()
        ganador = s.last_winner
        if any(c.rank == 7 and c.suit == s.trump_card.suit for c in s.players[ganador].hand):
            self.skipTest("en esta mano sí tiene el siete")
        with self.assertRaises(BriscaError) as ctx:
            cambiar_triunfo(s, ganador)
        self.assertEqual(ctx.exception.code, "no_seven")


class PartidaTests(unittest.TestCase):
    def test_el_empate_a_60_anula_el_juego(self):
        s = partida(2)
        mitad = [
            carta(1, "o"), carta(3, "c"), carta(12, "e"), carta(11, "b"), carta(10, "o"),
            carta(1, "c"), carta(3, "e"), carta(12, "b"), carta(11, "o"), carta(10, "c"),
        ]
        s.players[0].won = list(mitad)
        s.players[1].won = [Card(rank=c.rank, suit=c.suit, copy=1) for c in mitad]
        s.deck = []
        s.trump_card = None
        s.players[0].hand = [carta(7, "o")]
        s.players[1].hand = [carta(6, "o")]
        play(s, 0, s.players[0].hand[0].id)
        play(s, 1, s.players[1].hand[0].id)

        self.assertNotEqual(s.phase, "playing")
        self.assertTrue(any(e["kind"] == "game-end" and e["anulado"] for e in s.events))
        self.assertEqual(s.games_won, [0, 0])

    def test_una_partida_entera_con_bots_termina_y_no_pierde_cartas(self):
        s = partida(2, seed=99)
        vueltas = 0
        while s.phase != "match-end" and vueltas < 400:
            vueltas += 1
            if s.phase == "game-end":
                next_game(s, random.Random(vueltas))
                continue
            play(s, s.turn, s.players[s.turn].hand[0].id)
        self.assertEqual(s.phase, "match-end")
        self.assertLess(vueltas, 400)
        self.assertTrue(any(g >= s.target_games for g in s.games_won))
        total = sum(len(p.hand) + len(p.won) for p in s.players)
        self.assertEqual(total + len(s.deck) + (1 if s.trump_card else 0), 40)

    def test_no_se_reparte_el_juego_siguiente_si_el_anterior_sigue_vivo(self):
        s = partida(2)
        with self.assertRaises(BriscaError) as ctx:
            next_game(s)
        self.assertEqual(ctx.exception.code, "not_finished")


class VistaTests(unittest.TestCase):
    def test_la_vista_trae_tu_mano_y_de_los_demas_solo_el_recuento(self):
        s = partida(2)
        vista = state_for(s, 1)
        self.assertEqual(len(vista["myHand"]), 3)
        self.assertNotIn("hand", vista["players"][0])
        self.assertEqual(vista["players"][0]["handCount"], 3)
        self.assertNotIn("deck", vista)
        self.assertEqual(vista["deckCount"], len(s.deck))

    def test_la_carta_que_pinta_si_se_ve(self):
        s = partida(2)
        vista = state_for(s, 0)
        self.assertEqual(vista["trumpCard"]["id"], s.trump_card.id)
        self.assertEqual(vista["trumpSuit"], s.trump_suit)


if __name__ == "__main__":
    unittest.main()
