"""Tests de la app de partidas.

Fijan el hallazgo A1 de `docs/AUDITORIA_PROYECTO.md`: el resultado de una partida
del modo local lo declara el navegador, así que **no** puede mover el ELO ni el
balance de victorias. Solo puntúan las partidas cuyo resultado decide el servidor
(las del póker online).
"""
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from apps.games.models import Game
from apps.users.models import UserProfile


class SelfReportedResultTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ana", "ana@example.com", "Zx9!pqLmn42")
        UserProfile.objects.get_or_create(user=self.user)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def _create_game(self):
        res = self.client.post("/api/games/create_game/", {}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        return Game.objects.get(pk=res.data["id"])

    def test_create_game_marca_la_partida_como_no_puntuable(self):
        game = self._create_game()
        self.assertFalse(game.rated, "el modo local no puede ser puntuable")

    def test_autoproclamarse_ganador_no_da_elo_ni_victorias(self):
        game = self._create_game()
        res = self.client.post(
            f"/api/games/{game.id}/finish/",
            {"winner": "ana", "player1_score": 9999, "player2_score": 0},
            format="json",
        )
        self.assertEqual(res.status_code, 200)

        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.win_count, 0, "no debe contar como victoria")
        self.assertEqual(self.user.profile.elo_rating, 1600, "el ELO no debe moverse")

        # El resultado sí queda en el historial.
        game.refresh_from_db()
        self.assertEqual(game.status, "finished")
        self.assertEqual(game.player1_score, 9999)

    def test_el_ranking_publico_no_sube(self):
        game = self._create_game()
        self.client.post(
            f"/api/games/{game.id}/finish/",
            {"winner": "ana", "player1_score": 9999, "player2_score": 0},
            format="json",
        )
        res = self.client.get("/api/leaderboard/")
        self.assertEqual(res.status_code, 200)
        filas = [e for e in res.data["data"] if e["user"]["username"] == "ana"]
        if filas:
            self.assertEqual(filas[0]["eloRating"], 1600)
            self.assertEqual(filas[0]["wins"], 0)

    def test_una_partida_puntuable_si_mueve_el_elo(self):
        """El mismo endpoint, con una partida verificada por el servidor, sí puntúa."""
        game = self._create_game()
        game.rated = True                      # como las crea el póker online
        game.save(update_fields=["rated"])

        res = self.client.post(
            f"/api/games/{game.id}/finish/",
            {"winner": "ana", "player1_score": 5, "player2_score": 3},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.win_count, 1)
        self.assertGreater(self.user.profile.elo_rating, 1600)

    def test_solo_los_participantes_pueden_cerrar_la_partida(self):
        game = self._create_game()
        intruso = User.objects.create_user("luis", "luis@example.com", "Zx9!pqLmn42")
        otro = APIClient()
        otro.force_authenticate(intruso)
        res = otro.post(f"/api/games/{game.id}/finish/", {"winner": "luis"}, format="json")
        # 404 y no 403: el ViewSet solo deja ver a cada uno sus partidas, así que desde fuera
        # esta partida «no existe». Es a propósito: un 403 confirmaría que existe.
        self.assertEqual(res.status_code, 404)

    def test_la_partida_no_expone_el_email_de_los_jugadores(self):
        game = self._create_game()
        res = self.client.get(f"/api/games/{game.id}/")
        self.assertEqual(res.status_code, 200)
        for campo in ("player1", "player2", "winner"):
            jugador = res.data.get(campo)
            if jugador:
                self.assertNotIn("email", jugador, f"{campo} no debe exponer el email")

class StreakTests(TestCase):
    """La racha debe ser de victorias CONSECUTIVAS y solo de partidas puntuables."""

    def setUp(self):
        self.user = User.objects.create_user("ana", "ana@example.com", "Zx9!pqLmn42")
        UserProfile.objects.get_or_create(user=self.user)
        self.rival = User.objects.create_user("luis", "luis@example.com", "Zx9!pqLmn42")
        UserProfile.objects.get_or_create(user=self.rival)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def _game(self, winner, rated=True, order=0):
        from django.utils import timezone

        g = Game.objects.create(
            player1=self.user, player2=self.rival, status="finished",
            winner=winner, rated=rated,
        )
        Game.objects.filter(pk=g.pk).update(
            finished_at=timezone.now() + timezone.timedelta(minutes=order)
        )
        return g

    def test_la_racha_se_corta_con_la_derrota(self):
        self._game(self.user, order=1)
        self._game(self.user, order=2)
        self._game(self.rival, order=3)      # derrota: corta la racha
        self._game(self.user, order=4)

        data = self.client.get("/api/users/me/stats/").data["data"]
        self.assertEqual(data["currentStreak"], 1, "tras perder, la racha vuelve a 1")
        self.assertEqual(data["longestStreak"], 2, "la mejor racha fueron 2 victorias")

    def test_las_partidas_no_puntuables_no_cuentan_para_la_racha(self):
        self._game(self.user, rated=False, order=1)
        data = self.client.get("/api/users/me/stats/").data["data"]
        self.assertEqual(data["currentStreak"], 0)
        self.assertEqual(data["longestStreak"], 0)
        self.assertEqual(data["wins"], 0)

