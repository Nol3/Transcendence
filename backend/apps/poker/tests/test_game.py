"""Reglas de la partida: ciegas, orden de acción, apuestas mínimas, all-in,
botes laterales, showdown y reparto de botes."""
from __future__ import annotations

from django.test import SimpleTestCase

from apps.poker.engine import (
    ALL_IN,
    CALL,
    CHECK,
    FLOP,
    FOLD,
    RAISE,
    RIVER,
    TURN,
    Hand,
    IllegalAction,
)

from .helpers import build_deck

BOARD5 = "2c 3d 7h Js 9c"


def hand(stacks, holes, board="", button=0, sb=5, bb=10, n_seats=None, bots=()):
    n = n_seats if n_seats is not None else len(stacks)
    deck = build_deck(holes, board, n)
    return Hand(stacks=list(stacks), button=button, small_blind=sb, big_blind=bb,
                deck_cards=deck, bots=bots).start()


class BlindAndOrderTests(SimpleTestCase):
    def test_ciegas_heads_up(self):
        h = hand([1000, 1000], {0: "As Kd", 1: "7c 8h"})
        self.assertEqual(h.seats[0].committed, 5)    # el botón pone la ciega pequeña
        self.assertEqual(h.seats[1].committed, 10)
        self.assertEqual(h.current_bet, 10)
        self.assertEqual(h.actor, 0)                 # preflop habla el botón

    def test_ciegas_tres_jugadores(self):
        h = hand([1000, 1000, 1000], {0: "As Kd", 1: "7c 8h", 2: "3c 9h"})
        self.assertEqual(h.seats[1].committed, 5)    # SB
        self.assertEqual(h.seats[2].committed, 10)   # BB
        self.assertEqual(h.actor, 0)                 # UTG

    def test_orden_postflop(self):
        h = hand([1000, 1000], {0: "As Kd", 1: "7c 8h"}, BOARD5)
        h.act(0, CALL)
        h.act(1, CHECK)               # el BB tiene opción preflop
        self.assertEqual(h.street, FLOP)
        self.assertEqual(h.actor, 1)  # postflop habla primero el BB (izq. del botón)

    def test_orden_postflop_tres(self):
        h = hand([1000, 1000, 1000], {0: "As Kd", 1: "7c 8h", 2: "3c 9h"}, BOARD5)
        h.act(0, CALL)
        h.act(1, CALL)
        h.act(2, CHECK)
        self.assertEqual(h.street, FLOP)
        self.assertEqual(h.actor, 1)


class BettingTests(SimpleTestCase):
    def test_apuesta_minima_preflop(self):
        h = hand([1000, 1000], {0: "As Kd", 1: "7c 8h"})
        with self.assertRaises(IllegalAction):
            h.act(0, RAISE, 15)          # el mínimo es 20 (10 + 10)
        h.act(0, RAISE, 20)
        self.assertEqual(h.current_bet, 20)

    def test_no_puedes_actuar_fuera_de_turno(self):
        h = hand([1000, 1000], {0: "As Kd", 1: "7c 8h"})
        with self.assertRaises(IllegalAction):
            h.act(1, CALL)

    def test_no_puedes_subir_mas_que_tu_stack(self):
        h = hand([100, 1000], {0: "As Kd", 1: "7c 8h"})
        with self.assertRaises(IllegalAction):
            h.act(0, RAISE, 500)

    def test_check_solo_si_no_hay_apuesta(self):
        h = hand([1000, 1000], {0: "As Kd", 1: "7c 8h"})
        with self.assertRaises(IllegalAction):
            h.act(0, CHECK)              # hay que igualar la ciega

    def test_acciones_legales_por_situacion(self):
        h = hand([1000, 1000], {0: "As Kd", 1: "7c 8h"})
        actions = {o["action"] for o in h.legal_actions()}
        self.assertEqual(actions, {FOLD, CALL, RAISE, ALL_IN})
        h.act(0, CALL)
        self.assertEqual({o["action"] for o in h.legal_actions()}, {FOLD, CHECK, RAISE, ALL_IN})

    def test_la_calle_se_cierra_al_igualar(self):
        h = hand([1000, 1000], {0: "As Kd", 1: "7c 8h"}, BOARD5)
        h.act(0, CALL)
        h.act(1, CHECK)
        self.assertEqual(h.street, FLOP)
        h.act(1, CHECK)
        h.act(0, CHECK)
        self.assertEqual(h.street, TURN)
        h.act(1, CHECK)
        h.act(0, CHECK)
        self.assertEqual(h.street, RIVER)

    def test_all_in_corto_no_reabre_la_accion(self):
        """Un all-in menor que la subida mínima no permite volver a subir a quien ya actuó."""
        h = hand([1000, 140, 1000], {0: "As Kd", 1: "7c 8h", 2: "3c 9h"}, BOARD5)
        h.act(0, RAISE, 100)             # subida completa
        h.act(1, ALL_IN)                 # 140 en total: subida corta (40 < 90)
        h.act(2, CALL)
        self.assertEqual(h.actor, 0)
        actions = {o["action"] for o in h.legal_actions()}
        self.assertEqual(actions, {FOLD, CALL}, "no debe poder resubir tras una subida corta")

    def test_subida_completa_si_reabre_la_accion(self):
        h = hand([1000, 1000, 1000], {0: "As Kd", 1: "7c 8h", 2: "3c 9h"}, BOARD5)
        h.act(0, RAISE, 100)
        h.act(1, RAISE, 300)             # subida completa
        h.act(2, CALL)
        self.assertEqual(h.actor, 0)
        self.assertIn(RAISE, {o["action"] for o in h.legal_actions()})

    def test_all_in_corto_ofrece_all_in_pero_no_subida(self):
        """Si el all-in no llega a la subida mínima, solo se ofrece el shove."""
        h = hand([1000, 1000], {0: "As Kd", 1: "7c 8h"})
        h.act(0, RAISE, 100)
        h.seats[1].stack = 100           # total disponible 110 < subida mínima (190)
        actions = [o["action"] for o in h.legal_actions()]
        self.assertIn(ALL_IN, actions)
        self.assertNotIn(RAISE, actions)

    def test_sin_fichas_para_igualar_el_call_es_all_in(self):
        h = hand([1000, 1000], {0: "As Kd", 1: "7c 8h"})
        h.act(0, RAISE, 100)
        h.seats[1].stack = 50            # el BB solo tiene 50 y necesita 90
        opts = {o["action"]: o for o in h.legal_actions()}
        self.assertNotIn(RAISE, opts)
        self.assertEqual(opts[CALL]["amount"], 50)   # iguala con todo lo que tiene


class EndOfHandTests(SimpleTestCase):
    def test_retirada_gana_el_bote_sin_showdown(self):
        h = hand([1000, 1000], {0: "As Kd", 1: "7c 8h"})
        h.act(0, FOLD)
        self.assertTrue(h.complete)
        self.assertFalse(h.result["showdown"])
        self.assertEqual(h.seats[1].stack, 1005)   # gana la ciega pequeña
        self.assertEqual(h.seats[0].stack, 995)
        self.assertEqual(h.result["revealed"], {})

    def test_apuesta_no_igualada_se_devuelve(self):
        h = hand([1000, 1000], {0: "As Kd", 1: "7c 8h"})
        h.act(0, RAISE, 100)
        h.act(1, FOLD)
        self.assertEqual(h.seats[0].stack, 1010)   # recupera 90 y gana la ciega grande
        self.assertEqual(h.seats[1].stack, 990)

    def test_all_in_preflop_reparte_todas_las_calles(self):
        h = hand([100, 100], {0: "As Kd", 1: "7c 8h"}, "2c 3d 4h 9s Tc")
        h.act(0, ALL_IN)
        h.act(1, CALL)
        self.assertTrue(h.complete)
        self.assertTrue(h.result["showdown"])
        self.assertEqual(len(h.result["board"]), 5)
        self.assertEqual(h.seats[0].stack, 200)    # el As alto gana
        self.assertEqual(h.seats[1].stack, 0)

    def test_showdown_reparte_el_bote_al_mejor(self):
        h = hand([1000, 1000], {0: "As Ad", 1: "Ks Kd"}, "2h 4d 6c 8s Td")
        h.act(0, CALL)
        h.act(1, CHECK)
        h.act(1, CHECK)
        h.act(0, CHECK)
        h.act(1, CHECK)
        h.act(0, CHECK)
        h.act(1, CHECK)
        h.act(0, CHECK)
        self.assertTrue(h.complete)
        self.assertEqual(h.seats[0].stack, 1010)   # los ases ganan la ciega
        self.assertEqual(h.seats[1].stack, 990)
        # Claves de texto: `revealed` viaja por el channel layer y msgpack (Redis)
        # no admite claves enteras. El front las lee con `String(seat)`.
        self.assertEqual(set(h.result["revealed"]), {"0", "1"})

    def test_botes_laterales_tres_all_in(self):
        h = hand([100, 200, 300], {0: "As Ad", 1: "Ks Kd", 2: "3c 9h"},
                 "2h 4d 6c 8s Td")
        h.act(0, ALL_IN)
        h.act(1, ALL_IN)
        h.act(2, ALL_IN)
        self.assertTrue(h.complete)
        pots = h.result["pots"]
        self.assertEqual([p["amount"] for p in pots], [300, 200])
        self.assertEqual(pots[0]["winners"][0]["seat"], 0)   # bote principal: ases
        self.assertEqual(pots[1]["winners"][0]["seat"], 1)   # bote lateral: reyes
        # El exceso no igualado del stack grande vuelve a su dueño.
        self.assertEqual([s.stack for s in h.seats], [300, 200, 100])
        self.assertEqual(sum(s.stack for s in h.seats), 600)

    def test_bote_dividido_con_ficha_impar(self):
        h = hand([5, 5, 5], {0: "Ah Kh", 1: "Ad Kd", 2: "5c 6d"}, BOARD5,
                 sb=1, bb=2)
        h.act(0, ALL_IN)
        h.act(1, ALL_IN)
        h.act(2, ALL_IN)
        self.assertTrue(h.complete)
        self.assertEqual(h.result["pots"][0]["amount"], 15)
        winners = {w["seat"]: w["amount"] for w in h.result["pots"][0]["winners"]}
        self.assertEqual(set(winners), {0, 1})       # empatan
        self.assertEqual(sorted(winners.values()), [7, 8])
        # La ficha impar va al primero a la izquierda del botón (asiento 1).
        self.assertEqual(winners[1], 8)
        self.assertEqual(sum(s.stack for s in h.seats), 15)

    def test_el_bote_cuadra_siempre(self):
        """Conservación de fichas: nadie gana ni pierde fichas por arte del motor."""
        for stacks, holes, board in [
            ([1000, 1000], {0: "As Kd", 1: "7c 8h"}, BOARD5),
            ([100, 200, 300], {0: "As Ad", 1: "Ks Kd", 2: "3c 9h"}, "2h 4d 6c 8s Td"),
            ([5, 5, 5], {0: "Ah Kh", 1: "Ad Kd", 2: "5c 6d"}, BOARD5),
        ]:
            with self.subTest(stacks=stacks):
                h = hand(stacks, holes, board, sb=1, bb=2)
                while not h.complete:
                    opts = h.legal_actions()
                    pick = next(o for o in opts if o["action"] in (CHECK, CALL, FOLD))
                    h.act(h.actor, pick["action"], pick.get("amount"))
                self.assertEqual(sum(s.stack for s in h.seats), sum(stacks))


class PrivacyTests(SimpleTestCase):
    def test_no_se_filtran_las_cartas_ajenas(self):
        h = hand([1000, 1000], {0: "As Kd", 1: "7c 8h"}, BOARD5)
        view0 = h.state_for(0)
        self.assertEqual(view0["seats"][0]["hole"], ["As", "Kd"])
        self.assertIsNone(view0["seats"][1]["hole"], "¡las cartas del rival deben estar ocultas!")
        self.assertEqual(view0["seats"][1]["hole_count"], 2)
        view_spectator = h.state_for(None)
        self.assertIsNone(view_spectator["seats"][0]["hole"])
        self.assertIsNone(view_spectator["seats"][1]["hole"])

    def test_al_terminar_por_retirada_no_se_revela_nada(self):
        h = hand([1000, 1000], {0: "As Kd", 1: "7c 8h"}, BOARD5)
        h.act(0, FOLD)
        self.assertIsNone(h.state_for(0)["seats"][1]["hole"])

    def test_en_showdown_si_se_revela(self):
        h = hand([1000, 1000], {0: "As Ad", 1: "Ks Kd"}, "2h 4d 6c 8s Td")
        h.act(0, CALL)
        h.act(1, CHECK)
        h.act(1, CHECK)
        h.act(0, CHECK)
        h.act(1, CHECK)
        h.act(0, CHECK)
        h.act(1, CHECK)
        h.act(0, CHECK)
        self.assertEqual(h.state_for(0)["seats"][1]["hole"], ["Ks", "Kd"])

    def test_las_acciones_legales_solo_para_quien_habla(self):
        h = hand([1000, 1000], {0: "As Kd", 1: "7c 8h"})
        self.assertEqual(h.state_for(1)["legal_actions"], [])
        self.assertTrue(h.state_for(0)["legal_actions"])
