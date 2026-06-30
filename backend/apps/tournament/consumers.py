"""WebSocket consumer for live tournament brackets.

Clients connect to /ws/tournaments/<id>?token=<jwt>. On connect we authenticate
the JWT, then send the current tournament snapshot and push updates whenever the
bracket changes (driven by `apps.tournament.services._broadcast`).
Group: tournament_<id>.

Security: the consumer NEVER trusts client-sent state. Inbound messages are
ignored — the authoritative bracket state is only ever emitted by the backend
through `_broadcast`. This prevents a connected client from injecting a forged
bracket into every viewer.
"""
import json
from urllib.parse import parse_qs

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer


class TournamentConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.tournament_id = self.scope['url_route']['kwargs']['tournament_id']
        self.group_name = f'tournament_{self.tournament_id}'

        # Authenticate via the JWT passed as a query-string token. Reject the
        # handshake (4401) when it is missing or invalid.
        user = await self._authenticate()
        if user is None:
            await self.close(code=4401)
            return
        self.scope['user'] = user

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        snapshot = await self._snapshot()
        if snapshot is not None:
            await self.send(text_data=json.dumps({
                'type': 'tournament_update',
                'tournament': snapshot,
            }))

    async def disconnect(self, close_code):
        # group_name only exists once the handshake was accepted.
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        # Intentionally a no-op. Bracket state is authoritative on the server and
        # is only ever broadcast by the backend; clients cannot push state.
        return

    async def tournament_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'tournament_update',
            'tournament': event.get('tournament'),
        }))

    async def match_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'match_update',
            'tournament': event.get('tournament'),
        }))

    @sync_to_async
    def _authenticate(self):
        """Validate the JWT from the query string; return the User or None."""
        query_string = self.scope.get('query_string', b'').decode()
        token = (parse_qs(query_string).get('token') or [None])[0]
        if not token:
            return None
        try:
            from rest_framework_simplejwt.authentication import JWTAuthentication

            auth = JWTAuthentication()
            validated = auth.get_validated_token(token)
            return auth.get_user(validated)
        except Exception:
            return None

    @sync_to_async
    def _snapshot(self):
        from .models import Tournament
        from .serializers import TournamentSerializer

        try:
            tournament = Tournament.objects.get(pk=self.tournament_id)
        except (Tournament.DoesNotExist, ValueError):
            return None
        return TournamentSerializer(tournament).data
