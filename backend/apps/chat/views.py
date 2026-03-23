"""Chat app views."""
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Message
from .serializers import MessageSerializer


class MessageViewSet(viewsets.ModelViewSet):
    """ViewSet for Message management."""
    serializer_class = MessageSerializer

    def get_queryset(self):
        """Get messages for the current user."""
        return Message.objects.filter(
            models.Q(sender=self.request.user) | models.Q(recipient=self.request.user)
        )

    @action(detail=False, methods=['post'])
    def send_message(self, request):
        """Send a message to another user."""
        recipient_id = request.data.get('recipient_id')
        content = request.data.get('content')

        message = Message.objects.create(
            sender=request.user,
            recipient_id=recipient_id,
            content=content
        )
        serializer = self.get_serializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def conversation(self, request):
        """Get conversation between current user and another user."""
        other_user_id = request.query_params.get('user_id')
        messages = Message.objects.filter(
            (models.Q(sender=request.user) & models.Q(recipient_id=other_user_id)) |
            (models.Q(sender_id=other_user_id) & models.Q(recipient=request.user))
        ).order_by('-created_at')
        
        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)
