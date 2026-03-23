"""Tournament app views."""
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Tournament, TournamentParticipant
from .serializers import TournamentSerializer, TournamentParticipantSerializer


class TournamentViewSet(viewsets.ModelViewSet):
    """ViewSet for Tournament management."""
    queryset = Tournament.objects.all()
    serializer_class = TournamentSerializer

    @action(detail=False, methods=['post'])
    def create_tournament(self, request):
        """Create a new tournament."""
        name = request.data.get('name')
        description = request.data.get('description', '')
        max_players = request.data.get('max_players', 8)

        tournament = Tournament.objects.create(
            name=name,
            description=description,
            creator=request.user,
            max_players=max_players
        )
        # Add creator as participant
        TournamentParticipant.objects.create(tournament=tournament, user=request.user)

        serializer = self.get_serializer(tournament)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """Join a tournament."""
        tournament = self.get_object()
        if TournamentParticipant.objects.filter(tournament=tournament, user=request.user).exists():
            return Response({'error': 'Already joined'}, status=status.HTTP_400_BAD_REQUEST)

        if tournament.participants.count() >= tournament.max_players:
            return Response({'error': 'Tournament is full'}, status=status.HTTP_400_BAD_REQUEST)

        participant = TournamentParticipant.objects.create(tournament=tournament, user=request.user)
        serializer = TournamentParticipantSerializer(participant)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """Leave a tournament."""
        tournament = self.get_object()
        try:
            participant = TournamentParticipant.objects.get(tournament=tournament, user=request.user)
            participant.delete()
            return Response({'success': 'Left tournament'})
        except TournamentParticipant.DoesNotExist:
            return Response({'error': 'Not in tournament'}, status=status.HTTP_400_BAD_REQUEST)
