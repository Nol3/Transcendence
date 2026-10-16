"""Evaluación y comparación de manos.

La prueba de fuego es `test_frecuencias_exhaustivas`: enumera las 2.598.960 manos
de 5 cartas y compara el reparto por categorías con las frecuencias oficiales del
póker. Es lento (~1 min), así que solo corre con `POKER_EXHAUSTIVE=1`.
"""
from __future__ import annotations

import itertools
import os
import random
from unittest import skipUnless

from django.test import SimpleTestCase

from apps.poker.engine import (
    FLUSH,
    FOUR_OF_A_KIND,
    FULL_HOUSE,
    HIGH_CARD,
    ONE_PAIR,
    STRAIGHT,
    STRAIGHT_FLUSH,
    THREE_OF_A_KIND,
    TWO_PAIR,
    Card,
    evaluate,
    evaluate_five,
    full_deck,
    parse_cards,
)

EXPECTED_FREQ = {
    HIGH_CARD: 1302540,
    ONE_PAIR: 1098240,
    TWO_PAIR: 123552,
    THREE_OF_A_KIND: 54912,
    STRAIGHT: 10200,
    FLUSH: 5108,
    FULL_HOUSE: 3744,
    FOUR_OF_A_KIND: 624,
    STRAIGHT_FLUSH: 40,
}


class CardTests(SimpleTestCase):
    def test_parse_y_formato(self):
        c = Card.parse("As")
        self.assertEqual((c.rank, c.suit), (14, 3))
        self.assertEqual(str(c), "As")
        self.assertEqual(str(Card.parse("td")), "Td")

    def test_parse_invalido(self):
        for bad in ("", "Xx", "A", "Az", "1s"):
            with self.assertRaises(ValueError):
                Card.parse(bad)

    def test_baraja_completa_y_sin_repetidas(self):
        deck = full_deck()
        self.assertEqual(len(deck), 52)
        self.assertEqual(len(set(deck)), 52)

    def test_barajado_reparte_52_sin_repetir(self):
        from apps.poker.engine import Deck

        d = Deck()
        d.shuffle()
        drawn = d.draw(52)
        self.assertEqual(len(set(drawn)), 52)
        with self.assertRaises(ValueError):
            d.draw(1)


class EvaluateTests(SimpleTestCase):
    def rank(self, text: str):
        return evaluate_five(parse_cards(text))

    def test_categorias(self):
        cases = [
            ("As Kd 9c 7h 4s", HIGH_CARD),
            ("As Ad 9c 7h 4s", ONE_PAIR),
            ("As Ad 9c 9h 4s", TWO_PAIR),
            ("As Ad Ac 7h 4s", THREE_OF_A_KIND),
            ("9c Td Jh Qs Kc", STRAIGHT),
            ("As Ks 9s 7s 4s", FLUSH),
            ("As Ad Ac 7h 7s", FULL_HOUSE),
            ("As Ad Ac Ah 4s", FOUR_OF_A_KIND),
            ("9s Ts Js Qs Ks", STRAIGHT_FLUSH),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(self.rank(text).category, expected, text)

    def test_rueda_escalera_y_escalera_de_color(self):
        wheel = self.rank("As 2d 3c 4h 5s")
        self.assertEqual(wheel.category, STRAIGHT)
        self.assertEqual(wheel.tiebreak, (5, 4, 3, 2, 1))  # el As juega de 1
        sf_wheel = self.rank("As 2s 3s 4s 5s")
        self.assertEqual(sf_wheel.category, STRAIGHT_FLUSH)
        self.assertEqual(sf_wheel.tiebreak, (5, 4, 3, 2, 1))

    def test_escalera_alta_gana_a_la_rueda(self):
        self.assertLess(self.rank("As 2d 3c 4h 5s"), self.rank("2c 3d 4h 5s 6c"))

    def test_mejor_mano_de_siete(self):
        # 7 cartas con color y pareja: gana el color.
        seven = parse_cards("As Ks 9s 7s 4s Ad Kd")
        self.assertEqual(evaluate(seven).category, FLUSH)
        # 7 cartas con escalera y trío: gana la escalera.
        seven2 = parse_cards("9c 9d 9h Ts Jd Qc Kd")
        self.assertEqual(evaluate(seven2).category, STRAIGHT)
        # 7 cartas con dos tríos: el full house usa el trío alto.
        seven3 = parse_cards("9c 9d 9h Ks Kd Kc 2s")
        rank = evaluate(seven3)
        self.assertEqual(rank.category, FULL_HOUSE)
        self.assertEqual(rank.tiebreak[:2], (13, 9))

    def test_desempate_lexicografico(self):
        """Los casos que fallaban con un score aditivo: ahora gana la mano correcta."""
        duels = [
            ("As Ks 9s 5s 2s", "Ah Kh 8h 6h 4h"),   # color: 9 > 8 en la 3ª carta
            ("As Ad 2c 2h Ks", "Kh Kd Qc Qh As"),   # doble pareja: los ases mandan
            ("9s 9d 9c As Kd", "9h 9s 9d Kh Qs"),   # trío: kicker A > K
            ("2s 2d As Kd Qc", "2h 2c Ks Qd Jh"),   # pareja: kickers A,K > K,Q
            ("2c 3d 4h 5s 6c", "Ah 2d 3c 4h 5s"),   # escalera al 6 gana a la rueda
        ]
        for a, b in duels:
            with self.subTest(a=a, b=b):
                self.assertGreater(evaluate_five(parse_cards(a)),
                                   evaluate_five(parse_cards(b)))

    def test_igualdad_exacta(self):
        a = evaluate_five(parse_cards("As Ks Qs Js Ts"))
        b = evaluate_five(parse_cards("Ah Kh Qh Jh Th"))
        self.assertEqual(a, b)  # misma mano por valor, distinto palo

    def test_orden_total_por_categoria(self):
        ordered = [
            "As Kd 9c 7h 4s",  # carta alta
            "As Ad 9c 7h 4s",  # pareja
            "As Ad 9c 9h 4s",  # doble pareja
            "As Ad Ac 7h 4s",  # trío
            "9c Td Jh Qs Kc",  # escalera
            "As Ks 9s 7s 4s",  # color
            "As Ad Ac 7h 7s",  # full
            "As Ad Ac Ah 4s",  # póker
            "9s Ts Js Qs Ks",  # escalera de color
        ]
        ranks = [self.rank(t) for t in ordered]
        for i in range(len(ranks) - 1):
            self.assertLess(ranks[i], ranks[i + 1])

    def test_invariantes_del_desempate(self):
        """El desempate debe describir exactamente las cartas de la mano."""
        rng = random.Random(20261011)
        deck = full_deck()
        for _ in range(20000):
            hand = rng.sample(deck, 5)
            rank = evaluate_five(hand)
            ranks = sorted((c.rank for c in hand), reverse=True)
            counts = {r: ranks.count(r) for r in set(ranks)}
            tb = rank.tiebreak
            if rank.category == HIGH_CARD:
                self.assertEqual(tb, tuple(ranks))
            elif rank.category == ONE_PAIR:
                self.assertEqual(counts[tb[0]], 2)
                kickers = [r for r in ranks if r != tb[0]]
                self.assertEqual(tb[1:4], tuple(kickers))
            elif rank.category == TWO_PAIR:
                self.assertEqual(counts[tb[0]], 2)
                self.assertEqual(counts[tb[1]], 2)
                self.assertGreater(tb[0], tb[1])
                kicker = [r for r in ranks if r not in (tb[0], tb[1])]
                self.assertEqual(tb[2], kicker[0])
            elif rank.category == THREE_OF_A_KIND:
                self.assertEqual(counts[tb[0]], 3)
                kickers = [r for r in ranks if r != tb[0]]
                self.assertEqual(tb[1:3], tuple(kickers))
            elif rank.category == FOUR_OF_A_KIND:
                self.assertEqual(counts[tb[0]], 4)
                self.assertEqual(tb[1], [r for r in ranks if r != tb[0]][0])
            elif rank.category == FULL_HOUSE:
                self.assertEqual(counts[tb[0]], 3)
                self.assertEqual(counts[tb[1]], 2)
            elif rank.category == FLUSH:
                self.assertEqual(tb, tuple(ranks))
            elif rank.category in (STRAIGHT, STRAIGHT_FLUSH):
                for i in range(4):
                    self.assertEqual(tb[i] - tb[i + 1], 1)
                wheel = tb[0] == 5 and 14 in counts
                if wheel:
                    self.assertEqual(tb, (5, 4, 3, 2, 1))

    def test_distribucion_aleatoria(self):
        """Comprobación rápida del reparto por categorías (200k manos al azar)."""
        rng = random.Random(4242)
        deck = full_deck()
        n = 200_000
        counts = {k: 0 for k in EXPECTED_FREQ}
        for _ in range(n):
            counts[evaluate_five(rng.sample(deck, 5)).category] += 1
        total = sum(EXPECTED_FREQ.values())
        for cat, expected in EXPECTED_FREQ.items():
            p = expected / total
            sigma = (p * (1 - p) / n) ** 0.5
            observed = counts[cat] / n
            with self.subTest(cat=cat):
                self.assertLess(abs(observed - p), 5 * sigma + 1e-6,
                                f"categoría {cat}: {observed:.5f} vs {p:.5f}")

    @skipUnless(os.environ.get("POKER_EXHAUSTIVE") == "1",
                "lento: ejecuta con POKER_EXHAUSTIVE=1")
    def test_frecuencias_exhaustivas(self):
        """Las 2.598.960 manos de 5 cartas: el reparto debe ser EXACTO."""
        counts = {k: 0 for k in EXPECTED_FREQ}
        deck = full_deck()
        for combo in itertools.combinations(deck, 5):
            counts[evaluate_five(combo).category] += 1
        self.assertEqual(sum(counts.values()), 2598960)
        self.assertEqual(counts, EXPECTED_FREQ)
