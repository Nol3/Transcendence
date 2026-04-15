"""Rate limiting for public API."""
from rest_framework.throttling import SimpleRateThrottle

from .models import ApiKey


class ApiKeyThrottle(SimpleRateThrottle):
    """
    100 requests / hour per API key.
    Applied only to requests authenticated with ApiKeyAuthentication.
    """

    scope = "api_key"

    def get_cache_key(self, request, view):
        if not isinstance(request.auth, ApiKey):
            return None  # Let other throttles handle non-apikey requests
        return self.cache_format % {
            "scope": self.scope,
            "ident": request.auth.key,
        }


class ApiKeyBurstThrottle(SimpleRateThrottle):
    """
    20 requests / minute burst limit per API key.
    Prevents hammering even within the hourly budget.
    """

    scope = "api_key_burst"

    def get_cache_key(self, request, view):
        if not isinstance(request.auth, ApiKey):
            return None
        return self.cache_format % {
            "scope": self.scope,
            "ident": request.auth.key,
        }
