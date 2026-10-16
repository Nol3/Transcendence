"""Chat app serializers."""
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.users.serializers import PublicUserSerializer

from .models import Message


class MessageSerializer(serializers.ModelSerializer):
    sender = PublicUserSerializer(read_only=True)
    recipient = PublicUserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'sender', 'recipient', 'content', 'created_at', 'is_read']


class SendMessageSerializer(serializers.Serializer):
    """Entrada de `POST /api/chat/messages/send_message/`.

    Valida antes de tocar la base de datos: sin esto, un destinatario inexistente
    provocaba un IntegrityError (500) y se podían enviar mensajes vacíos.
    """

    recipient_id = serializers.IntegerField()
    content = serializers.CharField(max_length=2000, allow_blank=False, trim_whitespace=True)

    def validate_recipient_id(self, value):
        try:
            self.recipient = User.objects.get(pk=value)
        except User.DoesNotExist:
            raise serializers.ValidationError(_("El usuario destinatario no existe.")) from None
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        if request is not None and self.recipient.pk == request.user.pk:
            raise serializers.ValidationError(_("No puedes enviarte mensajes a ti mismo."))
        return attrs

    def create(self, validated_data):
        request = self.context['request']
        return Message.objects.create(
            sender=request.user,
            recipient=self.recipient,
            content=validated_data['content'],
        )
