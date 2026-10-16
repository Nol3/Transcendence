"""Chat app views."""
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Message
from .serializers import MessageSerializer, SendMessageSerializer


class MessageViewSet(viewsets.ModelViewSet):
    """ViewSet for Message management."""

    serializer_class = MessageSerializer
    # El chat no se edita ni se borra desde la API: solo se lee y se envía.
    http_method_names = ['get', 'post', 'head', 'options']

    def create(self, request, *args, **kwargs):
        """Aquí no se crea nada: los mensajes se envían por `send_message`.

        El `create` del ModelViewSet intentaba construir un mensaje con un serializador que
        tiene `sender` y `recipient` como solo lectura, así que `POST /api/chat/messages/`
        reventaba con un 500 (`NOT NULL constraint failed`).
        """
        return Response(
            {"detail": "Usa /api/chat/messages/send_message/ para enviar un mensaje."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def get_queryset(self):
        """Mensajes en los que participa el usuario, del más nuevo al más viejo."""
        return (
            Message.objects.filter(
                Q(sender=self.request.user) | Q(recipient=self.request.user)
            )
            .select_related('sender', 'recipient')
            .order_by('-created_at')
        )

    @action(detail=False, methods=['post'])
    def send_message(self, request):
        """Envía un mensaje a otro usuario."""
        serializer = SendMessageSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        message = serializer.save()
        return Response(
            MessageSerializer(message).data, status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=['get'])
    def conversation(self, request):
        """Conversación entre el usuario actual y otro usuario."""
        other_user_id = request.query_params.get('user_id')
        if not other_user_id or not str(other_user_id).isdigit():
            return Response(
                {'error': 'Falta el parámetro user_id (id numérico del otro usuario).'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        messages = (
            Message.objects.filter(
                (Q(sender=request.user) & Q(recipient_id=other_user_id))
                | (Q(sender_id=other_user_id) & Q(recipient=request.user))
            )
            .select_related('sender', 'recipient')
            .order_by('-created_at')
        )
        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def mark_read(self, request):
        """Marca como leídos los mensajes recibidos de otro usuario."""
        other_user_id = request.data.get('user_id')
        if not other_user_id or not str(other_user_id).isdigit():
            return Response(
                {'error': 'Falta el campo user_id (id numérico del otro usuario).'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        updated = Message.objects.filter(
            sender_id=other_user_id, recipient=request.user, is_read=False
        ).update(is_read=True)
        return Response({'marked_read': updated})
