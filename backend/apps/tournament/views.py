"""Tournament app views."""
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Tournament, TournamentMatch, TournamentParticipant
from .serializers import (
    MatchResultSerializer,
    TournamentCreateSerializer,
    TournamentParticipantSerializer,
    TournamentSerializer,
)
from .services import generate_bracket, report_match_result


class TournamentViewSet(viewsets.ModelViewSet):
    """Torneos: se ven todos, pero solo se modifican los que has creado.

    Sin esto, `PATCH`/`DELETE /api/tournament/<id>/` funcionaba sobre el torneo de
    cualquier otro (y con él, su bracket entero).
    """

    def get_queryset(self):
        """Los torneos se ven todos, pero cada acción tiene su dueño.

        Sin filtrar, `PATCH`/`DELETE /api/tournament/<id>/` funcionaba sobre el torneo de
        cualquier otro. El filtro depende de la acción: borrar es cosa de quien lo creó, y
        reportar o confirmar resultados también es cosa de los **participantes** (que no son
        el creador), así que a esos hay que dejarles llegar.
        """
        if self.action in ("list", "retrieve"):
            return Tournament.objects.all().order_by("-created_at")
        if self.action == "destroy":
            return Tournament.objects.filter(creator=self.request.user)
        return (
            Tournament.objects.filter(
                Q(creator=self.request.user) | Q(participants__user=self.request.user)
            )
            .distinct()
            .order_by("-created_at")
        )

    """ViewSet for Tournament management."""
    queryset = Tournament.objects.all()
    serializer_class = TournamentSerializer

    @action(detail=False, methods=['post'])
    def create_tournament(self, request):
        """Create a new tournament after validating the payload."""
        serializer = TournamentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        tournament = Tournament.objects.create(
            name=data['name'],
            description=data.get('description', ''),
            creator=request.user,
            max_players=data['max_players'],
        )
        # Add creator as participant
        TournamentParticipant.objects.create(tournament=tournament, user=request.user)

        output = self.get_serializer(tournament)
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """Join a tournament. Generates the bracket once it fills up.

        The capacity check and the participant insert run inside a single
        transaction with a row lock on the Tournament (`select_for_update`), so
        concurrent joins serialize and can never overshoot `max_players`.
        """
        # Resolve + permission-check via the router (404/permissions) first.
        self.get_object()

        with transaction.atomic():
            tournament = Tournament.objects.select_for_update().get(pk=pk)

            if tournament.status != 'pending':
                return Response(
                    {'error': 'Tournament already started'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if TournamentParticipant.objects.filter(
                tournament=tournament, user=request.user
            ).exists():
                return Response({'error': 'Already joined'}, status=status.HTTP_400_BAD_REQUEST)

            if tournament.participants.count() >= tournament.max_players:
                return Response({'error': 'Tournament is full'}, status=status.HTTP_400_BAD_REQUEST)

            participant = TournamentParticipant.objects.create(
                tournament=tournament, user=request.user
            )

            # Auto-seed round 1 when the tournament reaches capacity (still under
            # the lock; generate_bracket is itself atomic and idempotent).
            if tournament.participants.count() == tournament.max_players:
                generate_bracket(tournament)

        serializer = TournamentParticipantSerializer(participant)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """Leave a tournament (only allowed before it starts)."""
        tournament = self.get_object()
        if tournament.status != 'pending':
            return Response(
                {'error': 'Cannot leave a tournament in progress'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            participant = TournamentParticipant.objects.get(
                tournament=tournament, user=request.user
            )
            participant.delete()
            return Response({'success': 'Left tournament'})
        except TournamentParticipant.DoesNotExist:
            return Response({'error': 'Not in tournament'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='matches/(?P<match_id>[^/.]+)/table')
    def match_table(self, request, pk=None, match_id=None):
        """Abre (o devuelve) la mesa de póker real donde se juega este match.

        Solo los dos participantes pueden pedirla. Devuelve el id de la mesa y la
        ruta del WebSocket; el resultado lo cerrará el servidor al terminar la
        partida, sin que nadie lo declare.
        """
        tournament = self.get_object()
        match = get_object_or_404(
            TournamentMatch, pk=match_id, tournament=tournament
        )

        if request.user.id not in (match.player1_id, match.player2_id):
            return Response(
                {'error': 'Solo los jugadores del match pueden abrir su mesa'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if match.player2_id is None:
            return Response(
                {'error': 'Este match no se juega: el rival pasó directo'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if match.status == 'completed':
            return Response(
                {'error': 'Este match ya está cerrado', 'winner_slot': match.winner_slot()},
                status=status.HTTP_409_CONFLICT,
            )

        from apps.poker.tournament_tables import TOURNAMENT_BLINDS, get_or_create_match_table

        table = get_or_create_match_table(match)
        rival = match.player2 if request.user.id == match.player1_id else match.player1

        return Response({
            'table_id': table.id,
            'ws_path': f'/ws/poker/table/{table.id}',
            'opponent': {'id': rival.id, 'username': rival.username},
            'small_blind': TOURNAMENT_BLINDS['small_blind'],
            'big_blind': TOURNAMENT_BLINDS['big_blind'],
            'starting_stack': TOURNAMENT_BLINDS['starting_stack'],
            'tournament': {'id': tournament.id, 'name': tournament.name},
            'match_id': match.id,
        })

    @action(detail=True, methods=['post'], url_path='matches/(?P<match_id>[^/.]+)/result')
    def report_result(self, request, pk=None, match_id=None):
        """Reporta el resultado de un match.

        El resultado **no** se acepta por declaración unilateral de un jugador:

        - el **creador** del torneo arbitra: lo que él diga cierra el match;
        - un **jugador** declara un ganador y el match queda `awaiting_confirmation`
          hasta que **el rival confirme el mismo ganador**;
        - si los dos declaran ganadores distintos, hay conflicto (409) y decide el
          creador.

        El bracket solo avanza cuando el match queda `completed`, así que nadie
        puede avanzar rondas declarándose vencedor.
        """
        tournament = self.get_object()
        match = get_object_or_404(
            TournamentMatch, pk=match_id, tournament=tournament
        )

        is_creator = tournament.creator_id == request.user.id
        is_player = request.user.id in (match.player1_id, match.player2_id)
        if not (is_creator or is_player):
            return Response(
                {'error': 'Not allowed to report this match'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if match.status == 'completed':
            return Response(
                {'error': 'This match is already completed'},
                status=status.HTTP_409_CONFLICT,
            )

        serializer = MatchResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        winner_slot = data['winner_slot']

        if is_creator:
            # El creador hace de árbitro: su decisión es definitiva.
            report_match_result(
                match,
                winner_slot=winner_slot,
                player1_score=data['player1_score'],
                player2_score=data['player2_score'],
            )
            tournament.refresh_from_db()
            return Response(self.get_serializer(tournament).data)

        # Jugador: hace falta la confirmación del rival.
        pending = match.status == 'awaiting_confirmation'
        already_reported = match.result_reported_by_id == request.user.id

        if pending and not already_reported:
            if match.result_winner_slot == winner_slot:
                # El rival confirma el mismo ganador → el match se cierra con los
                # marcadores que declaró quien lo reportó.
                report_match_result(
                    match,
                    winner_slot=winner_slot,
                    player1_score=match.player1_score,
                    player2_score=match.player2_score,
                )
                tournament.refresh_from_db()
                return Response(self.get_serializer(tournament).data)
            return Response(
                {
                    'error': 'Result conflict',
                    'detail': 'El rival declaró otro ganador: decide el creador del torneo.',
                    'reported_winner_slot': match.result_winner_slot,
                },
                status=status.HTTP_409_CONFLICT,
            )

        # Primera declaración (o el mismo jugador la corrige): queda pendiente.
        match.status = 'awaiting_confirmation'
        match.result_winner_slot = winner_slot
        match.result_reported_by = request.user
        match.player1_score = data['player1_score']
        match.player2_score = data['player2_score']
        match.save(update_fields=[
            'status', 'result_winner_slot', 'result_reported_by',
            'player1_score', 'player2_score',
        ])
        tournament.refresh_from_db()
        return Response(self.get_serializer(tournament).data)
