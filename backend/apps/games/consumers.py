"""WebSocket consumers for game rooms and matchmaking.

- RoomConsumer        → /ws/rooms/<id>     group: room_<id>
- MatchmakingConsumer → /ws/matchmaking    process-wide waiting queue

The channel layer defaults to the in-memory backend (see settings), which is
fine for a single Daphne process. Swap in channels-redis for multi-process.
"""
import json
import uuid
from collections import deque

from channels.generic.websocket import AsyncWebsocketConsumer


class RoomConsumer(AsyncWebsocketConsumer):
    """Relays room presence/state to everyone watching a given room."""

    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.group_name = f'room_{self.room_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send(text_data=json.dumps({
            'type': 'room_update',
            'room': {'id': self.room_id, 'status': 'waiting'},
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        try:
            payload = json.loads(text_data) if text_data else {}
        except json.JSONDecodeError:
            return
        await self.channel_layer.group_send(
            self.group_name,
            {'type': 'room_update', 'room': payload.get('room', {})},
        )

    async def room_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'room_update',
            'room': event.get('room'),
        }))


class MatchmakingConsumer(AsyncWebsocketConsumer):
    """Pairs the two oldest waiting clients into a shared room id.

    `_waiting` is a process-level queue of channel names. When a second player
    arrives we pop the pair and notify both with the same generated room id.
    """

    _waiting: "deque[str]" = deque()

    async def connect(self):
        # No group_add here: a consumer already receives layer messages sent to
        # its own channel_name, and channel_name (contains "!") is not a valid
        # *group* name. We use channel_layer.send(channel_name, ...) directly.
        await self.accept()

        if MatchmakingConsumer._waiting:
            opponent = MatchmakingConsumer._waiting.popleft()
            room_id = uuid.uuid4().hex[:12]
            for channel in (opponent, self.channel_name):
                await self.channel_layer.send(channel, {
                    'type': 'match_found',
                    'room_id': room_id,
                })
        else:
            MatchmakingConsumer._waiting.append(self.channel_name)
            await self.send(text_data=json.dumps({'type': 'searching'}))

    async def disconnect(self, close_code):
        try:
            MatchmakingConsumer._waiting.remove(self.channel_name)
        except ValueError:
            pass

    async def match_found(self, event):
        await self.send(text_data=json.dumps({
            'type': 'match_found',
            'roomId': event.get('room_id'),
        }))
