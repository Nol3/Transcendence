"""Historial de manos y estadísticas del póker.

Al acabar una partida se guardan las manos jugadas (tablero, bote, ganadores y
participantes) y se exponen por API **solo al dueño de la partida**.
"""
from asgiref.sync import async_to_sync
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from apps.games.models import Game
from apps.poker.bots import decide
from apps.poker.models import PokerHandPlayer, PokerHandRecord
from apps.poker.services import report_match_end
from apps.poker.tables import TableSeat, registry
from apps.users.models import UserProfile


class PokerHistoryTests(TestCase):
    def setUp(self):
        self.ana = User.objects.create_user("ana", "ana@example.com", "Zx9!pqLmn42")
        self.luis = User.objects.create_user("luis", "luis@example.com", "Zx9!pqLmn42")
        self.otro = User.objects.create_user("otro", "otro@example.com", "Zx9!pqLmn42")
        for u in (self.ana, self.luis, self.otro):
            UserProfile.objects.get_or_create(user=u)
        self.client = APIClient()
        self.client.force_authenticate(self.ana)

    def tearDown(self):
        for table in registry.all():
            registry.drop(table.id)

    def _jugar_partida(self, rival: User | None, stack: int = 40):
        """Juega una partida heads-up hasta el final y guarda su historial."""
        asientos = [
            TableSeat(index=0, user_id=self.ana.id, username=self.ana.username, stack=stack),
        ]
        if rival is None:
            asientos.append(TableSeat(index=1, username="Bot Test", stack=stack, is_bot=True))
        else:
            asientos.append(TableSeat(index=1, user_id=rival.id, username=rival.username,
                                      stack=stack))
        table = registry.create(asientos, small_blind=5, big_blind=10)
        table.start()

        for _ in range(600):
            if table.finished:
                break
            if table.hand is None or table.hand.complete:
                table._start_hand()
                continue
            idx = table.hand.actor
            if idx is None:
                break
            accion, amount = decide(table.hand, idx, table.rng)
            table.hand.act(idx, accion, amount)
            async_to_sync(table._after_action)()

        self.assertTrue(table.finished, "la partida debe terminar")
        async_to_sync(report_match_end)(table)
        return table

    # ── Guardado ────────────────────────────────────────────────────────────
    def test_al_acabar_la_partida_se_guardan_las_manos(self):
        table = self._jugar_partida(None)
        self.assertTrue(table.hands, "la mesa debe haber acumulado manos")

        game = Game.objects.filter(player1=self.ana).order_by("-id").first()
        self.assertIsNotNone(game)
        registros = PokerHandRecord.objects.filter(game=game).order_by("hand_number")
        self.assertEqual(registros.count(), len(table.hands))

        primera = registros.first()
        self.assertEqual(primera.table_id, table.id)
        self.assertGreater(primera.pot, 0, "el bote debe quedar registrado")
        self.assertTrue(primera.winner_names, "debe haber al menos un ganador")

        jugadores = list(primera.players.order_by("seat"))
        self.assertEqual(len(jugadores), 2)
        self.assertEqual(jugadores[0].name, self.ana.username)
        self.assertTrue(jugadores[1].is_bot)
        self.assertEqual(jugadores[0].user_id, self.ana.id)
        # Las fichas de la última mano coinciden con el stack final de la mesa.
        ultima = registros.last()
        mio = ultima.players.get(seat=0)
        self.assertEqual(mio.stack_after, table.seats[0].stack)

    def test_las_cartas_solo_se_guardan_si_hubo_showdown(self):
        self._jugar_partida(None)
        for mano in PokerHandRecord.objects.all():
            for jugador in mano.players.all():
                if mano.showdown and not jugador.folded:
                    continue          # en showdown puede haber cartas reveladas
                if not mano.showdown:
                    self.assertEqual(jugador.hole, "", "sin showdown no se revelan cartas")

    def test_una_partida_humano_humano_tambien_guarda_historial(self):
        table = self._jugar_partida(self.luis)
        game = Game.objects.filter(poker_hands__isnull=False).order_by("-id").first()
        self.assertIsNotNone(game)
        self.assertGreater(game.poker_hands.count(), 0)
        # Los dos jugadores aparecen con su usuario (no son bots).
        mano = game.poker_hands.first()
        self.assertFalse(any(j.is_bot for j in mano.players.all()))
        self.assertEqual({j.user_id for j in mano.players.all()}, {self.ana.id, self.luis.id})
        self.assertTrue(table.finished)

    # ── API ─────────────────────────────────────────────────────────────────
    def test_el_historial_lista_mis_partidas(self):
        self._jugar_partida(None)
        res = self.client.get("/api/poker/history/")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["count"], 1)
        fila = res.data["results"][0]
        self.assertIn("opponent", fila)
        self.assertIn(fila["result"], ("win", "loss", "draw"))
        self.assertGreaterEqual(fila["hands"], 1)

    def test_el_historial_no_hace_una_consulta_por_partida(self):
        """El resumen de cada fila costaba cuatro consultas sueltas (la última mano, sus dos
        jugadores y el recuento): ocho con dos partidas, ochenta con veinte. Ahora las manos y
        sus jugadores van precargados y el recuento viene anotado, así que el número de
        consultas **no crece** con las filas.
        """
        self._jugar_partida(None)
        self._jugar_partida(self.luis)

        # Tres consultas para cualquier número de filas: las partidas, las manos y sus
        # jugadores. Si alguien mete una consulta por partida, este número sube y el test cae.
        with self.assertNumQueries(3):
            res = self.client.get("/api/poker/history/")

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["count"], 2)

    def test_el_detalle_devuelve_las_manos(self):
        self._jugar_partida(None)
        game = Game.objects.filter(poker_hands__isnull=False).order_by("-id").first()
        res = self.client.get(f"/api/poker/history/{game.id}/")
        self.assertEqual(res.status_code, 200, res.data)
        manos = res.data["results"]
        self.assertGreaterEqual(len(manos), 1)
        self.assertIn("board", manos[0])
        self.assertIn("players", manos[0])
        self.assertIn("winner_names", manos[0])

    def test_no_puedo_ver_la_partida_de_otro(self):
        self._jugar_partida(None)
        game = Game.objects.filter(poker_hands__isnull=False).order_by("-id").first()
        ajeno = APIClient()
        ajeno.force_authenticate(self.otro)
        res = ajeno.get(f"/api/poker/history/{game.id}/")
        self.assertEqual(res.status_code, 403)

    def test_las_estadisticas_cuentan_mis_manos(self):
        self._jugar_partida(None)
        res = self.client.get("/api/poker/stats/")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["hands_played"],
                         PokerHandPlayer.objects.filter(user=self.ana).count())
        self.assertGreaterEqual(res.data["hands_played"], 1)
        self.assertGreater(res.data["biggest_pot"], 0)
        self.assertLessEqual(res.data["hands_won"], res.data["hands_played"])

    def test_el_historial_no_filtra_emails(self):
        self._jugar_partida(self.luis)
        game = Game.objects.filter(poker_hands__isnull=False).order_by("-id").first()
        for url in ("/api/poker/history/", f"/api/poker/history/{game.id}/", "/api/poker/stats/"):
            res = self.client.get(url)
            self.assertNotIn("@example.com", str(res.data), url)

    def test_sin_sesion_no_hay_historial(self):
        anon = APIClient()
        for url in ("/api/poker/history/", "/api/poker/stats/"):
            self.assertIn(anon.get(url).status_code, (401, 403), url)

    def test_sin_manos_el_historial_esta_vacio(self):
        res = self.client.get("/api/poker/history/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["count"], 0)
        self.assertEqual(self.client.get("/api/poker/stats/").data["hands_played"], 0)
