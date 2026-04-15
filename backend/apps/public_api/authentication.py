"""API key authentication backend."""
from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import ApiKey


class ApiKeyAuthentication(BaseAuthentication):
    """
    Authenticate via X-API-Key header.

    Usage:
        X-API-Key: <your-api-key>
    """

    keyword = "X-API-Key"

    def authenticate(self, request):
        raw_key = request.META.get("HTTP_X_API_KEY")
        if not raw_key:
            return None  # Not our auth scheme — try next authenticator

        try:
            api_key = ApiKey.objects.select_related("user").get(
                key=raw_key, is_active=True
            )
        except ApiKey.DoesNotExist:
            raise AuthenticationFailed("Invalid or revoked API key.")

        # Track last usage without blocking the request
        ApiKey.objects.filter(pk=api_key.pk).update(last_used_at=timezone.now())

        return (api_key.user, api_key)

    def authenticate_header(self, request):
        return self.keyword
