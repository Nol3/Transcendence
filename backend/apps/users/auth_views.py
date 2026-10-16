"""Custom authentication views compatible with frontend."""

import contextlib

from django.conf import settings
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.serializers import RegisterSerializer, UserSerializer


class LoginView(APIView):
    """Custom login view compatible with frontend."""

    permission_classes = [AllowAny]
    # Límite propio y más estricto que el general: aquí es donde se prueban contraseñas.
    # `ScopedRateThrottle` es el que mira `throttle_scope`; los generales (anónimo y usuario)
    # se siguen aplicando además.
    throttle_classes = [AnonRateThrottle, ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response(
                {"error": _("Email and password are required")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Try to find user by email or username
        from django.contrib.auth.models import User

        # `filter().first()` y no `get()`: con dos cuentas con el mismo email, `get()` lanza
        # `MultipleObjectsReturned` y el login devolvía 500 para siempre (bastaba con que
        # alguien registrara el email de la víctima para dejarla fuera).
        user = User.objects.filter(email__iexact=email).order_by("id").first()
        if user is None:
            user = User.objects.filter(username__iexact=email).order_by("id").first()
        if user is None:
            return Response(
                {"error": _("Invalid credentials")},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Authenticate with username
        user = authenticate(username=user.username, password=password)
        if user is None:
            return Response(
                {"error": _("Invalid credentials")}, status=status.HTTP_401_UNAUTHORIZED
            )

        # Generate tokens
        refresh = RefreshToken.for_user(user)

        # Build user data
        user_data = UserSerializer(user).data

        return Response(
            {
                "data": {
                    "user": user_data,
                    "tokens": {
                        "accessToken": str(refresh.access_token),
                        "refreshToken": str(refresh),
                    },
                }
            },
            status=status.HTTP_200_OK,
        )


class RegisterView(APIView):
    """Custom register view compatible with frontend."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            # Surface the first validation message in the flat "error" shape the
            # frontend already understands, while keeping field detail too.
            first_error = next(iter(serializer.errors.values()))
            message = first_error[0] if isinstance(first_error, list) else str(first_error)
            return Response(
                {"error": message, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = serializer.save()

        # Generate tokens
        refresh = RefreshToken.for_user(user)

        # Build user data
        user_data = UserSerializer(user).data

        return Response(
            {
                "data": {
                    "user": user_data,
                    "tokens": {
                        "accessToken": str(refresh.access_token),
                        "refreshToken": str(refresh),
                    },
                }
            },
            status=status.HTTP_201_CREATED,
        )


class MeView(APIView):
    """Get current user. Requires authentication."""

    def get(self, request):
        if not request.user or not request.user.is_authenticated:
            return Response(
                {"error": _("User not authenticated")},
                status=status.HTTP_401_UNAUTHORIZED
            )
        user_data = UserSerializer(request.user).data
        return Response({"data": {"user": user_data}})


class RefreshTokenView(APIView):
    """Refresca el acceso **y rota** el refresh.

    Antes devolvía `str(refresh)`, es decir el **mismo** token de siempre: como la rotación de
    SimpleJWT solo afecta a su propia vista y esta es propia, el refresh era eterno dentro de
    sus 7 días y no había forma de revocarlo. Ahora se emite uno nuevo con otro `jti` y el
    usado entra en la lista negra, así que un refresh robado deja de servir en cuanto se usa.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get("refreshToken")

        if not refresh_token:
            return Response(
                {"error": _("Refresh token is required")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            refresh = RefreshToken(refresh_token)
            # El orden importa: se revoca el jti actual y **después** se cambia por uno nuevo.
            refresh.blacklist()
            refresh.set_jti()
            refresh.set_exp()
            refresh.set_iat()
            return Response(
                {
                    "data": {
                        "tokens": {
                            "accessToken": str(refresh.access_token),
                            "refreshToken": str(refresh),
                        }
                    }
                }
            )
        except Exception:
            return Response(
                {"error": _("Invalid refresh token")}, status=status.HTTP_401_UNAUTHORIZED
            )


class LogoutView(APIView):
    """Cierra la sesión de verdad: el refresh que se manda queda revocado.

    Antes devolvía 200 y no hacía nada (el comentario lo admitía), así que «cerrar sesión»
    dejaba el refresh vivo 7 días más. Es `AllowAny` a propósito: la credencial aquí es
    **poseer** el refresh, y quien no lo tenga no puede revocar el de nadie.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get("refreshToken")
        if refresh_token:
            # Un token ya caducado o inventado no es un problema para quien se va.
            with contextlib.suppress(Exception):
                RefreshToken(refresh_token).blacklist()
        return Response({"message": "Logged out successfully"})


class GoogleLoginView(APIView):
    """
    Verify a Google Identity Services credential (ID token) and return app JWT.

    Flow:
      1. Frontend gets `credential` from Google (GSI One Tap or Sign-In button).
      2. POST { "credential": "<google-jwt>" } to this endpoint.
      3. Backend verifies signature/audience with google-auth library.
      4. Creates or retrieves the Django user by email.
      5. Returns same JWT envelope as normal login.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        credential = request.data.get("credential")
        if not credential:
            return Response(
                {"error": _("Google credential is required")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        client_id = settings.GOOGLE_CLIENT_ID
        if not client_id:
            return Response(
                {"error": _("Google OAuth is not configured on the server")},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Verify the token with Google's public keys
        try:
            id_info = google_id_token.verify_oauth2_token(
                credential,
                google_requests.Request(),
                client_id,
                clock_skew_in_seconds=30,
            )
        except ValueError as exc:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Google ID token verification failed: {exc}")
            return Response(
                {"error": f"Invalid Google token: {exc}"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        email = id_info.get("email")
        email_verified = id_info.get("email_verified", False)

        if not email or not email_verified:
            return Response(
                {"error": _("Google account email is not verified")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        given_name = id_info.get("given_name", "")

        from django.contrib.auth.models import User

        from apps.users.models import UserProfile

        # Get or create the user
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "username": self._unique_username(email, given_name),
                "first_name": id_info.get("given_name", ""),
                "last_name": id_info.get("family_name", ""),
            },
        )

        if created:
            user.set_unusable_password()  # Google-only account — no password
            user.save()
            UserProfile.objects.get_or_create(user=user)

        # Generate app JWT tokens
        refresh = RefreshToken.for_user(user)
        user_data = UserSerializer(user).data

        return Response(
            {
                "data": {
                    "user": user_data,
                    "tokens": {
                        "accessToken": str(refresh.access_token),
                        "refreshToken": str(refresh),
                    },
                    "is_new_user": created,
                }
            },
            status=status.HTTP_200_OK,
        )

    def _unique_username(self, email: str, given_name: str) -> str:
        """Derive a unique username from email or given_name."""
        import re

        from django.contrib.auth.models import User

        base = given_name.lower() if given_name else email.split("@")[0]
        base = re.sub(r"[^a-z0-9_]", "", base)[:20] or "user"

        candidate = base
        suffix = 1
        while User.objects.filter(username=candidate).exists():
            candidate = f"{base}{suffix}"
            suffix += 1
        return candidate
