"""Tests del motor del Mus en el servidor.

Mismos casos que los del front (`mus-engine.spec.ts`): las reglas están escritas dos veces y la
única forma de que no se separen es probarlas igual en los dos sitios.
"""
from __future__ import annotations

import random
import unittest

from apps.baraja import Card
from apps.mus.bots import bot_decision
from apps.mus.engine import (
    JUGADORES,
    LANCES,
    PIEDRAS_PARA_GANAR,
    MusError,
    comparar,
    cortar_mus,
    decir_mus,
    descartar,
    envidar,
    evaluar,
    fuerza_mus,
    new_game,
    next_hand,
    no_quiero,
    ordago,
    orden_juego,
    pareja_de,
    pasar,
    quiero,
    state_for,
    turno_actual,
)
from apps.mus.juego import MusJuego


def carta(rank: int, suit: str = "o", copy: int = 0) -> Card:
    return Card(rank=rank, suit=suit, copy=copy)


def partida(seed: int = 5):
    return new_game(names=["A", "B", "C", "D"], bots=[False] * 4, rng=random.Random(seed))


def manos_base():
    return [
        [carta(12), carta(7), carta(4), carta(1)],
        [carta(11), carta(6), carta(5), carta(2)],
        [carta(10), carta(7, "c"), carta(4, "c"), carta(1, "c")],
        [carta(7, "e"), carta(6, "e"), carta(5, "e"), carta(2, "e")],
    ]


def mesa(manos):
    """Monta una mesa con manos concretas, ya en la fase de lances."""
    s = partida()
    for i, p in enumerate(s.players):
        p.hand = list(manos[i])
        p.jugada = evaluar(manos[i])
        p.hablado = False
    s.phase = "lances"
    s.lance = "grande"
    return s


class OrdenTests(unittest.TestCase):
    def test_el_tres_vale_lo_mismo_que_el_rey_y_el_dos_que_el_as(self):
        self.assertEqual(fuerza_mus(carta(3)), fuerza_mus(carta(12)))
        self.assertEqual(fuerza_mus(carta(2)), fuerza_mus(carta(1)))

    def test_de_mayor_a_menor(self):
        orden = [fuerza_mus(carta(r)) for r in (12, 3, 11, 10, 7, 6, 5, 4, 1, 2)]
        self.assertEqual(orden, sorted(orden, reverse=True))


class JugadasTests(unittest.TestCase):
    def test_grande_y_chica(self):
        j = evaluar([carta(12), carta(7), carta(4), carta(1)])
        self.assertEqual(j.grande, fuerza_mus(carta(12)))
        self.assertEqual(j.chica, fuerza_mus(carta(1)))

    def test_parejas_por_categorias(self):
        self.assertEqual(evaluar([carta(12), carta(12, "c"), carta(7), carta(7, "c")]).pares_categoria, "duples")
        self.assertEqual(evaluar([carta(12), carta(12, "c"), carta(12, "e"), carta(12, "b")]).pares_categoria, "duples")
        self.assertEqual(evaluar([carta(12), carta(12, "c"), carta(12, "e"), carta(7)]).pares_categoria, "medias")
        self.assertEqual(evaluar([carta(12), carta(12, "c"), carta(7), carta(4)]).pares_categoria, "par")
        self.assertIsNone(evaluar([carta(12), carta(7), carta(4), carta(1)]).pares_categoria)

    def test_a_igualdad_de_pares_gana_la_carta_mas_alta(self):
        con_reyes = evaluar([carta(12), carta(12, "c"), carta(4), carta(1)])
        con_cuatros = evaluar([carta(4), carta(4, "c"), carta(12), carta(1)])
        self.assertGreater(comparar(con_reyes, con_cuatros, "pares"), 0)

    def test_el_juego_y_el_punto(self):
        # Para el juego el tres vale 3: 3 + 10 + 10 + 10 = 33.
        self.assertEqual(evaluar([carta(3), carta(10), carta(12), carta(11)]).juego, 33)
        # Para el punto el tres vale 10 (como el rey): 40.
        self.assertEqual(evaluar([carta(3), carta(10), carta(12), carta(11)]).punto, 40)
        self.assertIsNone(evaluar([carta(7), carta(6), carta(5), carta(4)]).juego)
        self.assertEqual(evaluar([carta(7), carta(6), carta(5), carta(4)]).punto, 22)

    def test_el_orden_del_juego(self):
        self.assertEqual(orden_juego(31), 0)  # la una, la mejor
        self.assertEqual(orden_juego(32), 1)
        self.assertEqual(orden_juego(40), 2)
        self.assertEqual(orden_juego(33), 7)  # la peor
        self.assertEqual(orden_juego(38), -1)
        self.assertEqual(orden_juego(39), -1)
        self.assertEqual(orden_juego(30), -1)

    def test_el_31_gana_a_cualquier_otro_juego(self):
        una = evaluar([carta(12), carta(11), carta(10), carta(1)])  # 31
        peor = evaluar([carta(3), carta(10), carta(12), carta(11)])  # 33
        self.assertEqual(una.juego, 31)
        self.assertGreater(comparar(una, peor, "juego"), 0)

    def test_sin_juego_se_va_al_punto(self):
        veintiocho = evaluar([carta(12), carta(7), carta(6), carta(5)])
        veintisiete = evaluar([carta(12), carta(7), carta(6), carta(4)])
        self.assertIsNone(veintiocho.juego)
        self.assertEqual(veintiocho.punto, 28)
        self.assertGreater(comparar(veintiocho, veintisiete, "juego"), 0)


class MusFaseTests(unittest.TestCase):
    def test_se_corta_una_sola_vez(self):
        s = partida()
        decir_mus(s, 0)  # habla el mano
        cortar_mus(s, 1)
        self.assertEqual(s.phase, "lances")
        self.assertEqual(s.lance, "grande")
        with self.assertRaises(MusError) as ctx:
            decir_mus(s, 2)
        self.assertEqual(ctx.exception.code, "not_mus")

    def test_si_todos_piden_mus_se_pasa_al_descarte(self):
        s = partida()
        for seat in (0, 1, 2, 3):
            decir_mus(s, seat)
        self.assertEqual(s.phase, "descartar")

    def test_se_habla_por_turno_empezando_por_el_mano(self):
        s = partida()
        with self.assertRaises(MusError) as ctx:
            decir_mus(s, 2)
        self.assertEqual(ctx.exception.code, "not_your_turn")
        decir_mus(s, 0)
        with self.assertRaises(MusError) as ctx:
            decir_mus(s, 0)
        self.assertEqual(ctx.exception.code, "not_your_turn")

    def test_se_descartan_cartas_y_se_vuelve_al_mus(self):
        s = partida()
        for seat in (0, 1, 2, 3):
            decir_mus(s, seat)
        antes = [c.id for c in s.players[0].hand]
        descartar(s, 0, [antes[0], antes[1]], random.Random(9))
        self.assertEqual(len(s.players[0].hand), 4)
        self.assertNotIn(antes[0], [c.id for c in s.players[0].hand])
        self.assertEqual(s.players[0].descartes, 1)


class EnvitesTests(unittest.TestCase):
    def test_quien_responde_es_siempre_de_la_pareja_contraria(self):
        s0 = mesa(manos_base())
        envidar(s0, 0, 2)
        self.assertNotEqual(pareja_de(s0.responde), pareja_de(0))

        tras_pasar = mesa(manos_base())
        pasar(tras_pasar, 0)
        envidar(tras_pasar, 1, 2)
        self.assertNotEqual(pareja_de(tras_pasar.responde), pareja_de(1))

    def test_el_envite_minimo_son_dos_piedras(self):
        s = mesa(manos_base())
        with self.assertRaises(MusError) as ctx:
            envidar(s, 0, 1)
        self.assertEqual(ctx.exception.code, "too_small")

    def test_no_querer_da_una_piedra_al_que_envido(self):
        s = mesa(manos_base())
        envidar(s, 0, 2)
        no_quiero(s, 1)
        self.assertEqual(s.teams[0].piedras, 1)
        self.assertIsNone(s.envite)

    def test_querer_resuelve_el_lance_con_lo_apostado(self):
        s = mesa([
            [carta(12), carta(12, "c"), carta(7), carta(4)],
            [carta(6), carta(5), carta(4, "c"), carta(1)],
            [carta(12, "e"), carta(12, "b"), carta(6, "c"), carta(5, "c")],
            [carta(7, "c"), carta(6, "e"), carta(5, "e"), carta(1, "c")],
        ])
        envidar(s, 0, 2)
        quiero(s, 1)
        # Grande (2 por ganarla) + las 2 apostadas.
        self.assertEqual(s.teams[0].piedras, 4)

    def test_no_se_envida_dos_veces_sin_resolver(self):
        s = mesa(manos_base())
        envidar(s, 0, 2)
        # Con un envite vivo, al que le toca es al que tiene que responder.
        with self.assertRaises(MusError) as ctx:
            envidar(s, s.responde, 3)
        self.assertEqual(ctx.exception.code, "betting")


class LancesYTanteoTests(unittest.TestCase):
    def test_los_lances_van_en_orden(self):
        self.assertEqual(LANCES, ("grande", "chica", "pares", "juego"))

    def test_pasando_los_cuatro_se_resuelve_el_lance(self):
        s = mesa(manos_base())
        for seat in (0, 1, 2, 3):
            pasar(s, seat)
        self.assertEqual(s.lance, "chica")
        self.assertEqual(s.teams[0].piedras, 2)  # la pareja 0 tiene el rey

    def test_en_pares_duples_valen_tres_medias_dos_y_pareja_una(self):
        def con_pares(mano0):
            s = mesa([mano0, *manos_base()[1:]])
            s.lance = "pares"
            for seat in (0, 1, 2, 3):
                pasar(s, seat)
            return s.teams[0].piedras

        self.assertEqual(con_pares([carta(12), carta(12, "c"), carta(7), carta(7, "c")]), 3)
        self.assertEqual(con_pares([carta(12), carta(12, "c"), carta(12, "e"), carta(12, "b")]), 3)
        self.assertEqual(con_pares([carta(12), carta(12, "c"), carta(12, "e"), carta(7)]), 2)
        self.assertEqual(con_pares([carta(12), carta(12, "c"), carta(7), carta(4)]), 1)

    def test_en_juego_un_31_vale_tres_y_otro_juego_dos(self):
        def con_juego(mano0):
            s = mesa([
                mano0,
                [carta(7, "c"), carta(6, "c"), carta(5, "c"), carta(4, "c")],
                [carta(7, "e"), carta(6, "e"), carta(5, "e"), carta(4, "e")],
                [carta(7, "b"), carta(6, "b"), carta(5, "b"), carta(4, "b")],
            ])
            s.lance = "juego"
            for seat in (0, 1, 2, 3):
                pasar(s, seat)
            return s.teams[0].piedras

        self.assertEqual(con_juego([carta(12), carta(11), carta(10), carta(1)]), 3)  # 31
        self.assertEqual(con_juego([carta(3), carta(10), carta(12), carta(11)]), 2)  # 33

    def test_llegar_a_cuarenta_termina_el_juego(self):
        s = mesa([
            [carta(12), carta(12, "c"), carta(7), carta(7, "c")],
            [carta(6), carta(5), carta(4), carta(1)],
            [carta(12, "e"), carta(12, "b"), carta(6, "c"), carta(5, "c")],
            [carta(7, "e"), carta(6, "e"), carta(5, "e"), carta(1, "c")],
        ])
        s.teams[0].piedras = PIEDRAS_PARA_GANAR - 2  # gana la grande: 2 piedras justas
        for seat in (0, 1, 2, 3):
            pasar(s, seat)
        self.assertGreaterEqual(s.teams[0].piedras, PIEDRAS_PARA_GANAR)
        self.assertEqual(s.teams[0].juegos, 1)
        self.assertEqual(s.phase, "game-end")

    def test_la_mano_siguiente_conserva_piedras_y_juegos(self):
        s = partida()
        s.teams[0].piedras = 12
        s.teams[1].juegos = 1
        next_hand(s, random.Random(3))
        self.assertEqual(s.teams[0].piedras, 12)
        self.assertEqual(s.teams[1].juegos, 1)
        self.assertEqual(s.phase, "mus")


class PartidaEnteraTests(unittest.TestCase):
    def test_una_partida_entre_cuatro_bots_llega_a_la_vaca(self):
        s = new_game(names=["A", "B", "C", "D"], bots=[True] * 4, rng=random.Random(11))
        vueltas = 0
        while s.phase != "vaca-end" and vueltas < 4000:
            vueltas += 1
            seat = turno_actual(s)
            if seat is None:
                next_hand(s, random.Random(vueltas))
                continue
            decision = bot_decision(s, seat)
            if decision is None:
                next_hand(s, random.Random(vueltas))
                continue
            accion, dato = decision
            if accion == "mus":
                decir_mus(s, seat)
            elif accion == "cortar":
                cortar_mus(s, seat)
            elif accion == "descartar":
                descartar(s, seat, list(dato or []), random.Random(vueltas))
            elif accion == "pasar":
                pasar(s, seat)
            elif accion == "envidar":
                envidar(s, seat, int(dato or 2))
            elif accion == "ordago":
                ordago(s, seat)
            elif accion == "quiero":
                quiero(s, seat)
            elif accion == "no_quiero":
                no_quiero(s, seat)
        self.assertEqual(s.phase, "vaca-end")
        self.assertLess(vueltas, 4000)
        self.assertEqual(max(s.teams[0].juegos, s.teams[1].juegos), 3)


class VistaTests(unittest.TestCase):
    def test_cada_uno_ve_su_mano_y_la_de_su_companero(self):
        s = partida()
        vista = state_for(s, 0)
        self.assertEqual(len(vista["myHand"]), 4)
        self.assertEqual(vista["companero"]["id"], 2)  # el 0 y el 2 son pareja
        self.assertNotIn("hand", vista["players"][1])
        self.assertNotIn("jugada", vista["players"][1])

    def test_las_parejas_son_cero_dos_contra_uno_tres(self):
        self.assertEqual(pareja_de(0), pareja_de(2))
        self.assertEqual(pareja_de(1), pareja_de(3))
        self.assertNotEqual(pareja_de(0), pareja_de(1))
        self.assertEqual(JUGADORES, 4)


class EnchufeTests(unittest.TestCase):
    def test_el_juego_esta_registrado(self):
        from apps.salas.juegos import JUEGOS

        self.assertIn("mus", JUEGOS)
        self.assertEqual(JUEGOS["mus"].min_jugadores, 4)
        self.assertEqual(JUEGOS["mus"].max_jugadores, 4)

    def test_el_servidor_rechaza_lo_que_no_vale(self):
        juego = MusJuego()
        s = juego.nuevo_estado(nombres=["a", "b", "c", "d"], bots=[False] * 4, opciones={})
        # Fuera de turno.
        self.assertEqual(juego.accion(s, 1, {"action": "mus"})[0], "not_your_turn")
        # Una acción que no existe.
        self.assertEqual(juego.accion(s, 0, {"action": "volar"})[0], "unknown_action")
        # Y descartar cuando no toca.
        self.assertEqual(juego.accion(s, 0, {"action": "descartar", "cards": []})[0], "not_discard")

    def test_el_bot_solo_juega_su_asiento(self):
        juego = MusJuego()
        s = juego.nuevo_estado(nombres=["ana", "b", "c", "d"], bots=[False, True, True, True], opciones={})
        # Es el turno de la jugadora: no le toca a ningún bot.
        self.assertIsNone(juego.turno_de_bot(s))
        juego.accion(s, 0, {"action": "cortar"})
        # Sigue siendo el turno de la jugadora: el bot no juega por ella.
        self.assertIsNone(juego.turno_de_bot(s))
        # Cuando ella pasa, le toca al primer bot.
        juego.accion(s, 0, {"action": "pasar"})
        self.assertEqual(juego.turno_de_bot(s), 1)


if __name__ == "__main__":
    unittest.main()
