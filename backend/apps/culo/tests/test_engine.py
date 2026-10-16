"""Reglas del Culo en el servidor.

Son los **mismos casos** que ya se probaban en el front (`culo-engine.spec.ts`), porque
el motor de Python es un port del de TypeScript: si los dos pasan lo mismo, el port es
fiel. Y aquí, además, se prueba lo que solo importa cuando se juega online: que la vista
de un jugador **no lleve las cartas de los demás**.
"""
import random
import unittest

from apps.culo.bots import bot_decision
from apps.culo.engine import (
    Card,
    GameState,
    Player,
    Trick,
    apply_swaps,
    assign_roles,
    build_deck,
    can_beat,
    can_play,
    combo_of,
    deal,
    do_pass,
    exchange_swaps,
    legal_combos,
    new_game,
    next_round,
    play,
    standings,
    state_for,
    strength,
)


def carta(rank: int, suit: str, copy: int = 0) -> Card:
    return Card(rank=rank, suit=suit, copy=copy)


def estado(manos, turn=0) -> GameState:
    return GameState(
        players=[
            Player(id=i, name=m["name"], is_bot=m.get("isBot", False),
                   hand=list(m["cards"]), place=m.get("place"))
            for i, m in enumerate(manos)
        ],
        turn=turn,
    )


class ValorDeLasCartasTests(unittest.TestCase):
    def test_ordena_de_menor_a_mayor_como_manda_el_juego(self):
        orden = [2, 3, 4, 5, 6, 7, 10, 11, 12, 1]
        fuerzas = [strength(carta(r, "c")) for r in orden]
        self.assertEqual(fuerzas, sorted(fuerzas))
        self.assertEqual(len(set(fuerzas)), len(fuerzas))

    def test_el_cinco_de_oros_es_la_carta_mas_alta(self):
        cinco_oros = carta(5, "o")
        self.assertGreater(strength(cinco_oros), strength(carta(1, "e")))
        for suit in ("c", "e", "b"):
            self.assertGreater(strength(cinco_oros), strength(carta(12, suit)))

    def test_el_cinco_de_oros_no_vale_lo_mismo_que_los_otros_cincos(self):
        self.assertNotEqual(strength(carta(5, "o")), strength(carta(5, "c")))


class JugadasTests(unittest.TestCase):
    def test_son_del_mismo_valor_o_no_son_jugada(self):
        self.assertIsNotNone(combo_of([carta(3, "o"), carta(3, "c")]))
        self.assertIsNone(combo_of([carta(3, "o"), carta(4, "c")]))
        self.assertIsNone(combo_of([]))

    def test_el_cinco_de_oros_no_se_juega_junto_a_otro_cinco(self):
        self.assertIsNone(combo_of([carta(5, "o"), carta(5, "c")]))

    def test_con_dos_barajas_dos_cartas_iguales_si_son_pareja(self):
        self.assertIsNotNone(combo_of([carta(7, "e", 0), carta(7, "e", 1)]))


class ResponderTests(unittest.TestCase):
    def setUp(self):
        self.mesa = Trick(cards=[carta(5, "c")], by=0, strength=5, count=1)

    def test_sin_nada_en_la_mesa_cualquier_jugada_vale(self):
        self.assertTrue(can_beat(1, combo_of([carta(2, "o")]), None))

    def test_hay_que_igualar_la_cantidad_exacta(self):
        self.assertFalse(can_beat(2, 6, self.mesa))
        self.assertTrue(can_beat(1, 6, self.mesa))

    def test_hay_que_superar_el_valor(self):
        self.assertFalse(can_beat(1, 4, self.mesa))
        self.assertFalse(can_beat(1, 5, self.mesa))  # igual no basta
        self.assertTrue(can_beat(1, 6, self.mesa))

    def test_las_jugadas_legales_respetan_cantidad_y_valor(self):
        s = estado([{"name": "ana", "cards": [carta(6, "o"), carta(6, "c"), carta(11, "o")]}])
        s.table = self.mesa  # una carta de valor 5
        jugadas = legal_combos(s, 0)
        # En la mesa hay UNA carta: la respuesta es UNA carta (la pareja de seises no vale).
        self.assertEqual([len(j) for j in jugadas], [1, 1])
        self.assertEqual(sorted(strength(j[0]) for j in jugadas), [6, 9])  # el Caballo vale 9

    def test_con_dos_cartas_en_la_mesa_la_respuesta_es_de_dos(self):
        s = estado([{"name": "ana", "cards": [carta(6, "o"), carta(6, "c"), carta(11, "o")]}])
        s.table = Trick(cards=[carta(4, "o"), carta(4, "c")], by=1, strength=4, count=2)
        jugadas = legal_combos(s, 0)
        self.assertEqual(len(jugadas), 1)
        self.assertEqual(sorted(c.id for c in jugadas[0]), ["6c-0", "6o-0"])


class TurnosYBazasTests(unittest.TestCase):
    def test_jugar_quita_las_cartas_y_las_pone_en_la_mesa(self):
        s = estado([
            {"name": "ana", "cards": [carta(3, "o"), carta(7, "c")]},
            {"name": "luis", "cards": [carta(11, "o")]},
        ])
        self.assertTrue(play(s, 0, [carta(3, "o")]))
        self.assertEqual([c.id for c in s.players[0].hand], ["7c-0"])
        self.assertEqual([c.id for c in s.table.cards], ["3o-0"])
        self.assertEqual(s.turn, 1)

    def test_no_deja_jugar_la_misma_carta_dos_veces(self):
        # Sin esta comprobación, mandar dos veces el mismo id colaba como «pareja» y el
        # jugador se descartaba de una sola carta.
        s = estado([
            {"name": "ana", "cards": [carta(3, "o"), carta(7, "c")]},
            {"name": "luis", "cards": [carta(11, "o")]},
        ])
        gemela = carta(3, "o")
        self.assertFalse(can_play(s, 0, [gemela, gemela]))
        self.assertFalse(play(s, 0, [gemela, gemela]))
        self.assertEqual(len(s.players[0].hand), 2)  # no se ha descartado nada

    def test_no_deja_jugar_fuera_de_turno_ni_con_cartas_ajenas(self):
        s = estado([
            {"name": "ana", "cards": [carta(3, "o")]},
            {"name": "luis", "cards": [carta(11, "o")]},
        ])
        self.assertFalse(can_play(s, 1, [carta(11, "o")]))  # no es su turno
        self.assertFalse(can_play(s, 0, [carta(11, "o")]))  # esa carta no es suya

    def test_quien_pasa_no_vuelve_a_entrar_en_la_misma_baza(self):
        s = estado([
            {"name": "ana", "cards": [carta(3, "o"), carta(10, "o")]},
            {"name": "luis", "cards": [carta(4, "o"), carta(11, "o")]},
            {"name": "eva", "cards": [carta(5, "o"), carta(12, "o")]},
        ])
        play(s, 0, [carta(3, "o")])
        do_pass(s, 1)
        play(s, 2, [carta(5, "o")])
        self.assertEqual(s.turn, 0)  # vuelve a ana: luis queda fuera de la baza
        self.assertIn(1, s.passed)

    def test_la_baza_se_cierra_cuando_todos_los_demas_pasan(self):
        s = estado([
            {"name": "ana", "cards": [carta(3, "o"), carta(10, "o")]},
            {"name": "luis", "cards": [carta(4, "o")]},
        ])
        play(s, 0, [carta(3, "o")])
        do_pass(s, 1)
        self.assertIsNone(s.table)
        self.assertEqual(s.turn, 0)
        self.assertEqual(s.passed, [])


class FinDeRondaTests(unittest.TestCase):
    def test_quedarse_sin_cartas_da_puesto(self):
        s = estado([
            {"name": "ana", "cards": [carta(3, "o")]},
            {"name": "luis", "cards": [carta(11, "o")]},
        ])
        play(s, 0, [carta(3, "o")])
        self.assertEqual(s.players[0].place, 1)

    def test_la_ronda_termina_cuando_solo_queda_uno_con_cartas(self):
        s = estado([
            {"name": "ana", "cards": [carta(3, "o")]},
            {"name": "luis", "cards": [carta(11, "o")]},
            {"name": "eva", "cards": [], "place": 1},
        ])
        play(s, 0, [carta(3, "o")])
        self.assertEqual(s.phase, "round-end")
        self.assertEqual(s.players[1].place, 3)  # el que se quedó con cartas es el último

    def test_con_tres_jugadores_no_hay_vices(self):
        s = estado([
            {"name": "ana", "cards": [], "place": 1},
            {"name": "luis", "cards": [], "place": 2},
            {"name": "eva", "cards": [], "place": 3},
        ])
        assign_roles(s)
        self.assertEqual([p.role for p in s.players], ["presidente", "neutro", "culo"])

    def test_con_cuatro_o_mas_hay_vicepresidente_y_viceculo(self):
        s = estado([
            {"name": "ana", "cards": [], "place": 1},
            {"name": "luis", "cards": [], "place": 2},
            {"name": "eva", "cards": [], "place": 3},
            {"name": "paz", "cards": [], "place": 4},
        ])
        assign_roles(s)
        self.assertEqual(
            [p.role for p in s.players],
            ["presidente", "vicepresidente", "viceculo", "culo"],
        )
        self.assertEqual([p.name for p in standings(s)], ["ana", "luis", "eva", "paz"])


class IntercambioTests(unittest.TestCase):
    def _con_roles(self) -> GameState:
        s = estado([
            {"name": "ana", "cards": [carta(2, "o"), carta(3, "c")]},       # culo
            {"name": "luis", "cards": [carta(12, "o"), carta(1, "e")]},     # presidente
            {"name": "eva", "cards": [carta(4, "o"), carta(5, "c")]},       # viceculo
            {"name": "paz", "cards": [carta(6, "o"), carta(7, "c")]},       # vicepresidente
        ])
        for p, rol in zip(s.players, ["culo", "presidente", "viceculo", "vicepresidente"],
                          strict=True):
            p.role = rol
        return s

    def test_el_culo_da_sus_dos_mejores_y_el_presidente_sus_dos_peores(self):
        swaps = exchange_swaps(self._con_roles())
        culo_al_presi = next(s for s in swaps if s["from"] == 0 and s["to"] == 1)
        presi_al_culo = next(s for s in swaps if s["from"] == 1 and s["to"] == 0)
        self.assertEqual(sorted(c.id for c in culo_al_presi["cards"]), ["2o-0", "3c-0"])
        self.assertEqual(sorted(c.id for c in presi_al_culo["cards"]), ["12o-0", "1e-0"])

    def test_el_viceculo_da_su_mejor_al_vicepresidente(self):
        swaps = exchange_swaps(self._con_roles())
        self.assertEqual(len(next(s for s in swaps if s["from"] == 2)["cards"]), 1)
        self.assertEqual(len(next(s for s in swaps if s["from"] == 3)["cards"]), 1)

    def test_el_intercambio_mueve_las_cartas_de_verdad(self):
        s = self._con_roles()
        apply_swaps(s, exchange_swaps(s))
        self.assertTrue({"2o-0", "3c-0"} <= {c.id for c in s.players[1].hand})
        self.assertTrue({"12o-0", "1e-0"} <= {c.id for c in s.players[0].hand})


class VistaPorJugadorTests(unittest.TestCase):
    def test_no_ensena_las_cartas_de_los_demas(self):
        s = estado([
            {"name": "ana", "cards": [carta(3, "o"), carta(7, "c")]},
            {"name": "luis", "cards": [carta(11, "o")]},
        ])
        vista = state_for(s, viewer_id=0)
        self.assertEqual(len(vista["players"][0]["hand"]), 2)   # las mías, enteras
        self.assertEqual(vista["players"][1]["hand"], [])       # las del rival, no
        self.assertEqual(vista["players"][1]["handCount"], 1)   # pero sé cuántas tiene

    def test_sin_identidad_no_se_ve_ninguna_mano(self):
        s = estado([{"name": "ana", "cards": [carta(3, "o")]}])
        self.assertEqual(state_for(s, None)["players"][0]["hand"], [])


class PartidaCompletaTests(unittest.TestCase):
    def test_siempre_termina_y_no_pierde_ni_inventa_cartas(self):
        for partida in range(40):
            n = 3 + (partida % 4)
            barajas = 1 if partida % 2 == 0 else 2
            rng = random.Random(partida)
            g = new_game(
                names=[f"j{i}" for i in range(n)],
                bots=[True] * n,
                decks=barajas,
                rng=rng,
            )
            total = len(build_deck(barajas))
            vueltas = 0
            while g.phase == "playing" and vueltas < 5000:
                turno = g.turn
                decision = bot_decision(g, turno, random.Random(partida + vueltas))
                if decision:
                    play(g, turno, decision)
                else:
                    do_pass(g, turno)
                vueltas += 1
                ids = [c.id for p in g.players for c in p.hand]
                self.assertEqual(len(set(ids)), len(ids), "carta duplicada")
                self.assertLessEqual(len(ids), total, "más cartas que la baraja")

            self.assertLess(vueltas, 5000, "la partida no terminó")
            self.assertEqual(g.phase, "round-end")
            roles = [p.role for p in g.players]
            self.assertEqual(roles.count("presidente"), 1)
            self.assertEqual(roles.count("culo"), 1)
            self.assertEqual(sorted(p.place for p in g.players), list(range(1, n + 1)))

    def test_la_ronda_siguiente_la_abre_el_presidente(self):
        s = estado([
            {"name": "ana", "cards": [], "place": 1},
            {"name": "luis", "cards": [], "place": 2},
            {"name": "eva", "cards": [], "place": 3},
        ])
        assign_roles(s)
        next_round(s, random.Random(1))
        self.assertEqual(s.turn, 0)  # ana es la presidenta
        self.assertEqual(s.round, 2)
        self.assertEqual(s.phase, "playing")
        self.assertTrue(all(p.hand for p in s.players))
        self.assertTrue(all(p.place is None for p in s.players))


class RepartoTests(unittest.TestCase):
    def test_reparte_todas_las_cartas(self):
        manos = deal(build_deck(1), 6)
        self.assertEqual(sum(len(m) for m in manos), 40)
        # Con 6 jugadores no salen iguales (40 cartas: cuatro se llevan 7 y dos 6), y
        # así es como se juega: el reparto se termina.
        self.assertEqual(sorted(len(m) for m in manos), [6, 6, 7, 7, 7, 7])

    def test_dos_barajas_dan_ochenta_cartas_y_copias_distintas(self):
        baraja = build_deck(2)
        self.assertEqual(len(baraja), 80)
        self.assertEqual(len({c.id for c in baraja}), 80)
