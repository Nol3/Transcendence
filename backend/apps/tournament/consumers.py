"""WebSocket consumer for live tournament brackets.

Clients connect to /ws/tournaments/<id>. On connect we send the current
tournament snapshot, then push updates whenever the bracket changes (driven by
`apps.tournament.services._broadcast`). Group: tournament_<id>.
"""
import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer


class TournamentConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.tournament_id = self.scope['url_route']['kwargs']['tournament_id']
        self.group_name = f'tournament_{self.tournament_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        snapshot = await self._snapshot()
        if snapshot is not None:
            await self.send(text_data=json.dumps({
                'type': 'tournament_update',
                'tournament': snapshot,
            }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        # Inbound messages are echoed to the group so all viewers stay in sync.
        try:
            payload = json.loads(text_data) if text_data else {}
        except json.JSONDecodeError:
            return
        await self.channel_layer.group_send(
            self.group_name,
            {'type': 'tournament_update', 'tournament': payload.get('tournament')},
        )

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
    def _snapshot(self):
        from .models import Tournament
        from .serializers import TournamentSerializer

        try:
            tournament = Tournament.objects.get(pk=self.tournament_id)
        except (Tournament.DoesNotExist, ValueError):
            return None
        return TournamentSerializer(tournament).data
