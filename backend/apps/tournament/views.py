"""Tournament app views."""
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction
from django.shortcuts import get_object_or_404

from .models import Tournament, TournamentParticipant, TournamentMatch
from .serializers import (
    TournamentSerializer,
    TournamentParticipantSerializer,
    TournamentCreateSerializer,
    MatchResultSerializer,
)
from .services import generate_bracket, report_match_result


class TournamentViewSet(viewsets.ModelViewSet):
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
            participant = TournamentParticipant.objects.get(tournament=tournament, user=request.user)
            participant.delete()
            return Response({'success': 'Left tournament'})
        except TournamentParticipant.DoesNotExist:
            return Response({'error': 'Not in tournament'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='matches/(?P<match_id>[^/.]+)/result')
    def report_result(self, request, pk=None, match_id=None):
        """Report the result of a match and advance the bracket."""
        tournament = self.get_object()
        match = get_object_or_404(
            TournamentMatch, pk=match_id, tournament=tournament
        )
        if match.player1 != request.user and match.player2 != request.user \
                and tournament.creator != request.user:
            return Response(
                {'error': 'Not allowed to report this match'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = MatchResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        report_match_result(
            match,
            winner_slot=data['winner_slot'],
            player1_score=data['player1_score'],
            player2_score=data['player2_score'],
        )

        tournament.refresh_from_db()
        return Response(self.get_serializer(tournament).data)
