"""API del historial de póker: partidas jugadas, manos y estadísticas.

Todo se lee del historial que se guarda al terminar cada partida
(`services._save_hands`), así que aquí no hay lógica de juego: solo consultas
**acotadas al usuario que pregunta**.
"""
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.games.models import Game

from .models import PokerHandPlayer, PokerHandRecord, PokerPreference
from .serializers import PokerHandReplaySerializer, PokerHandSerializer


def _mis_partidas(user):
    """Partidas de póker del usuario, de la más reciente a la más antigua.

    Las manos van **precargadas** con sus jugadores, y el número de manos viene anotado: el
    resumen de cada fila necesita la última mano y las dos pilas, y sin esto eran cuatro
    consultas por partida (unas 80 para una lista de veinte).
    """
    return (
        Game.objects.filter(status='finished', poker_hands__isnull=False)
        .filter(Q(player1=user) | Q(player2=user))
        .annotate(num_manos=Count('poker_hands', distinct=True))
        .prefetch_related(
            Prefetch(
                'poker_hands',
                queryset=PokerHandRecord.objects.order_by('hand_number').prefetch_related('players'),
            )
        )
        .distinct()
        .select_related('player1', 'player2', 'winner')
        .order_by('-finished_at', '-id')
    )


def _resumen_partida(game, user) -> dict:
    """Fila del listado: rival, resultado, fichas y número de manos."""
    rival = game.player2 if game.player1_id == user.id else game.player1
    mi_asiento = 1 if game.player1_id == user.id else 2

    # `poker_hands` viene precargado y en orden: la última es la de más número.
    manos = list(game.poker_hands.all())
    ultima = manos[-1] if manos else None
    # Los asientos se separan en Python a propósito: los jugadores vienen precargados, y un
    # `.filter()` o un `.exclude()` sobre una relación precargada lanzan igualmente otra
    # consulta por partida — el N+1 volvía a entrar por aquí.
    mias = []
    suyos = []
    if ultima is not None:
        jugadores = list(ultima.players.all())
        mias = [j for j in jugadores if j.seat == mi_asiento - 1]
        suyos = [j for j in jugadores if j.seat != mi_asiento - 1]

    mi_stack = mias[0].stack_after if mias else (game.player1_score if mi_asiento == 1
                                                 else game.player2_score)
    rival_stack = (game.player2_score if mi_asiento == 1 else game.player1_score)
    if suyos:
        rival_stack = suyos[0].stack_after

    resultado = 'draw' if game.winner_id is None else 'win' if game.winner_id == user.id else 'loss'

    return {
        'game_id': game.id,
        'opponent': {'id': rival.id, 'username': rival.username} if rival else None,
        'result': resultado,
        'my_stack': mi_stack,
        'opponent_stack': rival_stack,
        'hands': game.num_manos,
        'rated': game.rated,
        'played_at': game.finished_at or game.played_at,
    }


class PokerHistoryView(APIView):
    """`GET /api/poker/history/` — mis últimas partidas de póker."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        limite = 20
        partidas = list(_mis_partidas(request.user)[:limite])
        return Response({
            'count': len(partidas),
            'results': [_resumen_partida(g, request.user) for g in partidas],
        })


class PokerMatchDetailView(APIView):
    """`GET /api/poker/history/<game_id>/` — las manos de una partida mía."""

    permission_classes = [IsAuthenticated]

    def get(self, request, game_id: int):
        game = get_object_or_404(Game, pk=game_id)
        if request.user.id not in (game.player1_id, game.player2_id):
            return Response(
                {'error': 'Esta partida no es tuya'},
                status=status.HTTP_403_FORBIDDEN,
            )
        manos = (
            game.poker_hands.prefetch_related('players')
            .order_by('hand_number')
        )
        return Response({
            'game_id': game.id,
            'results': PokerHandSerializer(manos, many=True).data,
        })


class PokerHandReplayView(APIView):
    """`GET /api/poker/history/hand/<hand_id>/` — una mano mía, con sus acciones.

    El registro de acciones es lo que permite reproducirla paso a paso. Se sirve
    aparte de la lista de manos (que es lo que se ve al entrar) porque es bastante
    más pesado y solo hace falta al abrir una mano concreta.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, hand_id: int):
        mano = get_object_or_404(
            PokerHandRecord.objects.prefetch_related('players'), pk=hand_id,
        )
        # Solo quien jugó la mano puede verla: el historial es de cada cual.
        if not mano.players.filter(user=request.user).exists():
            return Response(
                {'error': 'Esta mano no es tuya'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(PokerHandReplaySerializer(mano).data)


class PokerPreferencesView(APIView):
    """`GET`/`PUT /api/poker/preferences/` — tema, ciegas y tamaño de mesa del jugador."""

    permission_classes = [IsAuthenticated]

    def _datos(self, request):
        from .consumers import STAKE_LEVELS, TABLE_SIZES

        pref, _ = PokerPreference.objects.get_or_create(user=request.user)
        datos = request.data or {}

        if 'theme' in datos:
            if datos['theme'] not in dict(PokerPreference.THEMES):
                return pref, {'error': f"tema no válido (usa {list(dict(PokerPreference.THEMES))})"}
            pref.theme = datos['theme']
        if 'stake' in datos:
            if datos['stake'] not in STAKE_LEVELS:
                return pref, {'error': f"nivel de ciegas no válido (usa {list(STAKE_LEVELS)})"}
            pref.stake = datos['stake']
        if 'table_size' in datos:
            try:
                size = int(datos['table_size'])
            except (TypeError, ValueError):
                return pref, {'error': 'tamaño de mesa no válido'}
            if size not in TABLE_SIZES:
                return pref, {'error': f"tamaño de mesa no válido (usa {list(TABLE_SIZES)})"}
            pref.table_size = size

        pref.save()
        return pref, None

    def _respuesta(self, pref):
        return {
            'theme': pref.theme,
            'stake': pref.stake,
            'table_size': pref.table_size,
            'themes': [t for t, _ in PokerPreference.THEMES],
            'updated_at': pref.updated_at,
        }

    def get(self, request):
        pref, _ = PokerPreference.objects.get_or_create(user=request.user)
        return Response(self._respuesta(pref))

    def put(self, request):
        pref, error = self._datos(request)
        if error:
            return Response(error, status=status.HTTP_400_BAD_REQUEST)
        return Response(self._respuesta(pref))


class PokerLiveTablesView(APIView):
    """`GET /api/poker/tables/` — mesas vivas, para poder entrar a mirarlas.

    Nota de escalado: el registro de mesas vive en memoria del proceso (una sola
    instancia de Daphne), igual que la cola.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .tables import registry

        mesas = [
            {
                'table_id': table.id,
                'seats': len(table.seats),
                'players': [s.username for s in table.seats],
                'small_blind': table.small_blind,
                'big_blind': table.big_blind,
                'hand_number': table.hand_number,
                'finished': table.finished,
                'tournament_id': (table.context or {}).get('tournament_id'),
            }
            for table in registry.all()
        ]
        # Las que están en juego, primero.
        mesas.sort(key=lambda m: (m['finished'], -m['hand_number']))
        return Response({'count': len(mesas), 'results': mesas})


class PokerStatsView(APIView):
    """`GET /api/poker/stats/` — estadísticas agregadas de mi póker."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        mias = PokerHandPlayer.objects.filter(user=request.user)
        total = mias.count()
        ganadas = mias.filter(won__gt=0).count()
        showdowns = mias.filter(hand__showdown=True).count()
        showdowns_ganados = mias.filter(hand__showdown=True, won__gt=0).count()
        bote_max = (
            mias.order_by('-hand__pot').values_list('hand__pot', flat=True).first() or 0
        )
        retiradas = mias.filter(folded=True).count()
        return Response({
            'hands_played': total,
            'hands_won': ganadas,
            'showdowns': showdowns,
            'showdowns_won': showdowns_ganados,
            'biggest_pot': bote_max,
            'folded': retiradas,
            'win_rate': round(ganadas * 100 / total, 1) if total else 0.0,
        })


class PokerAchievementsView(APIView):
    """`GET /api/poker/achievements/` — logros del jugador (roadmap 7.1)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .achievements import logros_de

        logros = logros_de(request.user)
        return Response({
            'achievements': logros,
            'unlocked': sum(1 for logro in logros if logro['unlocked']),
            'total': len(logros),
        })
