"""Los matches de un torneo se juegan en mesas de póker reales.

Dos cosas se fijan aquí:

1. el endpoint que abre la mesa del match (solo los dos participantes, idempotente);
2. que el resultado lo cierra **el servidor** cuando la mesa termina: nadie declara
   su propia victoria, así que el bracket no se puede ama;ar (hallazgo A2).
"""
from asgiref.sync import async_to_sync
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from apps.poker.services import report_match_end
from apps.poker.tables import registry
from apps.poker.tournament_tables import TOURNAMENT_BLINDS, get_or_create_match_table
from apps.tournament.models import Tournament, TournamentMatch, TournamentParticipant
from apps.tournament.services import generate_bracket
from apps.users.models import UserProfile


class MatchTableTests(TestCase):
    def setUp(self):
        self.users = [User.objects.create_user(f"j{i}", f"j{i}@example.com", "Zx9!pqLmn42")
                      for i in range(4)]
        for u in self.users:
            UserProfile.objects.get_or_create(user=u)
        self.creator = self.users[0]
        self.t = Tournament.objects.create(name="Copa", creator=self.creator, max_players=4)
        for u in self.users:
            TournamentParticipant.objects.create(tournament=self.t, user=u)
        generate_bracket(self.t)
        self.t.refresh_from_db()
        self.match = (
            self.t.rounds.get(number=1).matches
            .exclude(player2=None).order_by("position").first()
        )
        self.p1, self.p2 = self.match.player1, self.match.player2

    def tearDown(self):
        # El registro de mesas vive en memoria: se limpia entre tests.
        for table in registry.all():
            registry.drop(table.id)

    def _client(self, user):
        c = APIClient()
        c.force_authenticate(user)
        return c

    def _open_table(self, user):
        return self._client(user).post(
            f"/api/tournament/{self.t.id}/matches/{self.match.id}/table/",
            {},
            format="json",
        )

    # ── El endpoint ──────────────────────────────────────────────────────────
    def test_abre_la_mesa_y_sienta_a_los_dos(self):
        res = self._open_table(self.p1)
        self.assertEqual(res.status_code, 200, res.data)
        self.assertTrue(res.data["table_id"])
        self.assertEqual(res.data["opponent"]["id"], self.p2.id)
        self.assertEqual(res.data["small_blind"], TOURNAMENT_BLINDS["small_blind"])

        table = registry.get(res.data["table_id"])
        self.assertIsNotNone(table)
        self.assertEqual([s.user_id for s in table.seats], [self.p1.id, self.p2.id])
        self.assertEqual(table.context["match_id"], self.match.id)
        self.assertEqual(table.context["tournament_id"], self.t.id)

    def test_los_dos_jugadores_acaban_en_la_misma_mesa(self):
        a = self._open_table(self.p1)
        b = self._open_table(self.p2)
        self.assertEqual(a.status_code, 200)
        self.assertEqual(b.status_code, 200)
        self.assertEqual(a.data["table_id"], b.data["table_id"])

    def test_la_mesa_no_reparte_hasta_que_estan_los_dos(self):
        table = get_or_create_match_table(self.match)
        self.assertIsNone(table.hand, "no debe haber mano sin los dos jugadores sentados")

    def test_un_desconocido_no_puede_abrir_la_mesa(self):
        intruso = User.objects.create_user("intruso", "i@example.com", "Zx9!pqLmn42")
        res = self._open_table(intruso)
        # 404 y no 403: el ViewSet de torneos solo deja ver aquellos en los que participas,
        # así que desde fuera el torneo (y su mesa) «no existen». Un 403 lo confirmaría.
        self.assertEqual(res.status_code, 404)

    def test_un_match_cerrado_no_abre_mesa(self):
        self.match.winner = self.p1
        self.match.status = "completed"
        self.match.save(update_fields=["winner", "status"])
        res = self._open_table(self.p1)
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.data["winner_slot"], 1)

    def test_un_pase_directo_no_tiene_mesa(self):
        # Match sin rival: se busca uno creado a mano para no depender del bracket.
        huerfano = TournamentMatch.objects.create(
            tournament=self.t, round=self.match.round, position=99,
            player1=self.p1, player2=None, status="pending",
        )
        res = self._client(self.p1).post(
            f"/api/tournament/{self.t.id}/matches/{huerfano.id}/table/", {}, format="json"
        )
        self.assertEqual(res.status_code, 400)

    # ── El servidor cierra el match ──────────────────────────────────────────
    def _termina_la_mesa_con(self, ganador: User):
        table = get_or_create_match_table(self.match)
        for seat in table.seats:
            seat.connected = True
        table.start()
        perdedor = [s for s in table.seats if s.user_id != ganador.id][0]
        perdedor.stack = 0
        table._finish_match("test: el rival se quedó sin fichas")
        self.assertEqual(table.winner.user_id, ganador.id)
        async_to_sync(report_match_end)(table)
        self.match.refresh_from_db()
        return table

    def test_el_servidor_cierra_el_match_sin_confirmacion(self):
        self._termina_la_mesa_con(self.p1)
        self.assertEqual(self.match.status, "completed")
        self.assertEqual(self.match.winner, self.p1)
        self.assertEqual(self.match.winner_slot(), 1)
        # Y el perdedor queda eliminado del torneo.
        self.assertTrue(
            TournamentParticipant.objects.get(tournament=self.t, user=self.p2).is_eliminated
        )

    def test_gana_el_asiento_2_y_el_resultado_va_por_usuario(self):
        self._termina_la_mesa_con(self.p2)
        self.assertEqual(self.match.status, "completed")
        self.assertEqual(self.match.winner, self.p2)
        self.assertEqual(self.match.winner_slot(), 2)

    def test_el_bracket_avanza_solo_al_cerrar_las_mesas(self):
        """Con los dos matches resueltos por el servidor, sale la siguiente ronda."""
        for match in self.t.rounds.get(number=1).matches.exclude(player2=None):
            table = get_or_create_match_table(match)
            for seat in table.seats:
                seat.connected = True
            table.start()
            ganador_id = match.player1_id
            for seat in table.seats:
                if seat.user_id != ganador_id:
                    seat.stack = 0
            table._finish_match("test")
            async_to_sync(report_match_end)(table)

        self.t.refresh_from_db()
        ronda1 = self.t.rounds.get(number=1)
        self.assertTrue(all(m.status == "completed" for m in ronda1.matches.all()))
        # 4 jugadores → 2 matches → la final (1 match) se genera sola.
        self.assertTrue(self.t.rounds.filter(number=2).exists())

    def test_una_mesa_sin_contexto_de_torneo_no_toca_ningun_match(self):
        """La mesa de la cola normal sigue registrando el Game y no toca torneos."""
        from apps.poker.tables import TableSeat

        table = registry.create(
            [
                TableSeat(index=0, user_id=self.p1.id, username=self.p1.username, stack=100),
                TableSeat(index=1, user_id=self.p2.id, username=self.p2.username, stack=100),
            ],
            small_blind=1, big_blind=2,
        )
        table.start()
        table.seats[1].stack = 0
        table._finish_match("test")
        resumen = async_to_sync(report_match_end)(table)
        self.assertIsNone(resumen)                     # report_match_end no devuelve nada
        self.match.refresh_from_db()
        self.assertEqual(self.match.status, "pending", "un match de torneo no se toca")
