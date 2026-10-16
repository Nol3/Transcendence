"""Tests del motor del Tute en el servidor.

Mismos casos que los del front (`tute-engine.spec.ts`): las reglas están escritas dos veces y la
única forma de que no se separen es probarlas igual en los dos sitios.
"""
from __future__ import annotations

import random
import unittest

from apps.baraja import Card
from apps.tute.engine import (
    ACUSE_OTRO,
    ACUSE_TRIUNFO,
    DIEZ_ULTIMAS,
    TuteError,
    acuses_disponibles,
    cantar,
    cantar_tute,
    cartas_por_jugador,
    jugadas_legales,
    new_game,
    next_game,
    play,
    state_for,
    tiene_tute,
)
from apps.tute.juego import TuteJuego


def carta(rank: int, suit: str, copy: int = 0) -> Card:
    return Card(rank=rank, suit=suit, copy=copy)


def partida(n: int = 2, seed: int = 7):
    return new_game(
        names=[f"J{i + 1}" for i in range(n)],
        bots=[i != 0 for i in range(n)],
        rng=random.Random(seed),
    )


def mesa(manos, baceta=None, triunfo="o", trick=None, last_winner=None):
    """Monta una mesa a mano. Siempre dos jugadores como mínimo: hace falta alguien al otro lado."""
    s = partida(max(2, len(manos)))
    for i, p in enumerate(s.players):
        p.hand = list(manos[i]) if i < len(manos) else []
        p.won = []
        p.cantados = 0
    s.baceta = list(baceta) if baceta else []
    s.trump_suit = triunfo
    s.trick = list(trick) if trick else []
    s.last_winner = last_winner
    s.cantado_en_esta_baza = []
    s.turn = 0
    return s


class RepartoTests(unittest.TestCase):
    def test_ocho_cartas_a_dos_y_trece_a_tres(self):
        self.assertEqual(cartas_por_jugador(2), 8)
        self.assertEqual(cartas_por_jugador(3), 13)
        s = partida(2)
        self.assertEqual([len(p.hand) for p in s.players], [8, 8])
        self.assertIsNotNone(s.trump_card)

    def test_no_se_pierde_ninguna_carta(self):
        s = partida(2)
        en_manos = sum(len(p.hand) for p in s.players)
        self.assertEqual(en_manos + len(s.baceta) + (1 if s.trump_card else 0), 40)


class ObligacionesTests(unittest.TestCase):
    """Aquí está el juego: qué se puede jugar cambia a mitad de la partida."""

    def test_con_baceta_solo_obliga_el_triunfo_y_sin_montar(self):
        s = mesa([[carta(2, "c"), carta(1, "e")]], baceta=[carta(4, "b")], triunfo="c",
                 trick=[(1, carta(7, "c"))])
        self.assertEqual([c.id for c in jugadas_legales(s, 0)], ["2c-0"])  # no monta al siete

    def test_con_baceta_si_sale_otro_palo_vale_cualquier_carta(self):
        s = mesa([[carta(2, "c"), carta(1, "e")]], baceta=[carta(4, "b")], triunfo="c",
                 trick=[(1, carta(7, "e"))])
        self.assertEqual(len(jugadas_legales(s, 0)), 2)

    def test_sin_baceta_hay_que_montar_si_se_puede(self):
        s = mesa([[carta(7, "o"), carta(2, "o")]], triunfo="c", trick=[(1, carta(4, "o"))])
        self.assertEqual([c.id for c in jugadas_legales(s, 0)], ["7o-0"])

    def test_sin_baceta_y_sin_poder_montar_asistes(self):
        # Ojo: el tres monta al siete, así que para "no poder montar" hay que usar cartas bajas.
        s = mesa([[carta(2, "o"), carta(4, "o")]], triunfo="c", trick=[(1, carta(7, "o"))])
        self.assertEqual(sorted(c.id for c in jugadas_legales(s, 0)), ["2o-0", "4o-0"])

    def test_sin_baceta_sin_del_palo_obligado_a_fallar(self):
        s = mesa([[carta(2, "c"), carta(4, "e")]], triunfo="c", trick=[(1, carta(7, "o"))])
        self.assertEqual([c.id for c in jugadas_legales(s, 0)], ["2c-0"])

    def test_sin_del_palo_y_sin_triunfo_contrafallo(self):
        s = mesa([[carta(2, "b"), carta(4, "e")]], triunfo="c", trick=[(1, carta(7, "o"))])
        self.assertEqual(len(jugadas_legales(s, 0)), 2)

    def test_jugar_una_carta_que_no_toca_se_rechaza(self):
        s = mesa([[carta(3, "o"), carta(2, "o")]], triunfo="c", trick=[(1, carta(7, "o"))])
        with self.assertRaises(TuteError) as ctx:
            play(s, 0, "2o-0")  # el tres monta al siete: obligado a jugarlo
        self.assertEqual(ctx.exception.code, "must_follow")


class AcusesTests(unittest.TestCase):
    def test_rey_y_caballo_del_triunfo_valen_40_y_de_otro_palo_20(self):
        s = mesa([[carta(12, "c"), carta(11, "c"), carta(12, "o"), carta(11, "o")]],
                 triunfo="c", last_winner=0)
        self.assertEqual(sorted(acuses_disponibles(s, 0)), ["c", "o"])
        cantar(s, 0, "c")
        self.assertEqual(s.players[0].cantados, ACUSE_TRIUNFO)
        self.assertTrue(s.events[-1]["cuarenta"])

        s2 = mesa([[carta(12, "o"), carta(11, "o")]], triunfo="c", last_winner=0)
        cantar(s2, 0, "o")
        self.assertEqual(s2.players[0].cantados, ACUSE_OTRO)

    def test_no_se_canta_sin_haber_ganado_la_baza(self):
        s = mesa([[carta(12, "c"), carta(11, "c")]], triunfo="c", last_winner=1)
        self.assertEqual(acuses_disponibles(s, 0), [])
        with self.assertRaises(TuteError) as ctx:
            cantar(s, 0, "c")
        self.assertEqual(ctx.exception.code, "not_your_trick")

    def test_solo_un_acuse_por_baza(self):
        s = mesa([[carta(12, "c"), carta(11, "c"), carta(12, "o"), carta(11, "o")]],
                 triunfo="c", last_winner=0)
        cantar(s, 0, "c")
        with self.assertRaises(TuteError) as ctx:
            cantar(s, 0, "o")
        self.assertEqual(ctx.exception.code, "already_sung")


class TuteYFinalTests(unittest.TestCase):
    def test_los_cuatro_reyes_ganan_al_instante(self):
        s = mesa([[carta(12, "o"), carta(12, "c"), carta(12, "e"), carta(12, "b")]], triunfo="c")
        self.assertTrue(tiene_tute(s, 0))
        cantar_tute(s, 0)
        self.assertEqual(s.phase, "match-end")
        self.assertEqual(s.winner, 0)

    def test_sin_los_cuatro_no_hay_tute(self):
        s = mesa([[carta(12, "o"), carta(12, "c"), carta(12, "e"), carta(11, "b")]], triunfo="c")
        self.assertFalse(tiene_tute(s, 0))
        with self.assertRaises(TuteError) as ctx:
            cantar_tute(s, 0)
        self.assertEqual(ctx.exception.code, "no_tute")

    def test_ganar_la_ultima_baza_vale_diez_tantos(self):
        s = mesa([[carta(1, "o")], [carta(2, "o")]], triunfo="c")
        s.trump_card = None  # ya no queda nada que robar: esta es la última baza
        play(s, 0, "1o-0")
        play(s, 1, "2o-0")
        self.assertNotEqual(s.phase, "playing")
        self.assertEqual(s.events[-1]["ultima"] if "ultima" in s.events[-1] else
                         next(e for e in s.events if e["kind"] == "game-end")["ultima"], 0)
        self.assertEqual(s.scores[0], 11 + DIEZ_ULTIMAS)
        self.assertEqual(s.scores[1], 0)

    def test_una_partida_entera_con_bots_termina_y_no_pierde_cartas(self):
        s = partida(2, seed=99)
        vueltas = 0
        while s.phase != "match-end" and vueltas < 600:
            vueltas += 1
            if s.phase == "game-end":
                next_game(s, random.Random(vueltas))
                continue
            legales = jugadas_legales(s, s.turn)
            play(s, s.turn, legales[0].id)
        self.assertEqual(s.phase, "match-end")
        self.assertLess(vueltas, 600)
        total = sum(len(p.hand) + len(p.won) for p in s.players)
        self.assertEqual(total + len(s.baceta) + (1 if s.trump_card else 0), 40)

    def test_no_se_reparte_el_juego_siguiente_si_el_anterior_sigue_vivo(self):
        with self.assertRaises(TuteError) as ctx:
            next_game(partida(2))
        self.assertEqual(ctx.exception.code, "not_finished")


class VistaTests(unittest.TestCase):
    def test_la_vista_trae_tu_mano_y_tus_jugadas_legales(self):
        s = partida(2)
        vista = state_for(s, 1)
        self.assertEqual(len(vista["myHand"]), 8)
        self.assertNotIn("hand", vista["players"][0])
        self.assertGreater(len(vista["jugadasLegales"]), 0)
        self.assertNotIn("baceta", vista)

    def test_las_jugadas_legales_de_la_vista_son_las_de_verdad(self):
        s = mesa([[carta(7, "o"), carta(2, "o")]], triunfo="c", trick=[(1, carta(4, "o"))])
        vista = state_for(s, 0)
        self.assertEqual(vista["jugadasLegales"], ["7o-0"])
        self.assertTrue(vista["obligaMontar"])


class EnchufeTests(unittest.TestCase):
    """Que el juego esté bien enchufado a la capa de salas."""

    def test_el_juego_esta_registrado(self):
        from apps.salas.juegos import JUEGOS

        self.assertIn("tute", JUEGOS)
        self.assertEqual(JUEGOS["tute"].min_jugadores, 2)

    def test_el_servidor_rechaza_lo_que_no_vale(self):
        juego = TuteJuego()
        s = juego.nuevo_estado(nombres=["ana", "luis"], bots=[False, False], opciones={})
        # Fuera de turno.
        error = juego.accion(s, 1, {"action": "play", "card": s.players[1].hand[0].id})
        self.assertEqual(error[0], "not_your_turn")
        # Una acción que no existe.
        self.assertEqual(juego.accion(s, 0, {"action": "volar"})[0], "unknown_action")
        # Y jugar una carta que no es tuya.
        ajena = s.players[1].hand[0].id
        self.assertEqual(juego.accion(s, 0, {"action": "play", "card": ajena})[0], "not_your_card")

    def test_el_bot_juega_cuando_le_toca(self):
        juego = TuteJuego()
        s = juego.nuevo_estado(nombres=["ana", "bot"], bots=[False, True], opciones={})
        # Empieza la jugadora (es mano): no le toca a ningún bot.
        self.assertEqual(s.turn, 0)
        self.assertIsNone(juego.turno_de_bot(s))

        # Juega ella y ya le toca al bot.
        juego.accion(s, 0, {"action": "play", "card": s.players[0].hand[0].id})
        self.assertEqual(juego.turno_de_bot(s), 1)
        antes = len(s.trick)
        juego.jugar_bot(s, 1)
        self.assertNotEqual(len(s.trick), antes)


if __name__ == "__main__":
    unittest.main()
