"""Custom authentication views compatible with frontend."""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from apps.users.serializers import UserSerializer
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
from django.conf import settings


class LoginView(APIView):
    """Custom login view compatible with frontend."""

    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response(
                {"error": "Email and password are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Try to find user by email or username
        from django.contrib.auth.models import User

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            try:
                user = User.objects.get(username=email)
            except User.DoesNotExist:
                return Response(
                    {"error": "Invalid credentials"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        # Authenticate with username
        user = authenticate(username=user.username, password=password)
        if user is None:
            return Response(
                {"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED
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
        username = request.data.get("username")
        email = request.data.get("email")
        password = request.data.get("password")

        if not username or not email or not password:
            return Response(
                {"error": "Username, email and password are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.contrib.auth.models import User
        from apps.users.models import UserProfile

        if User.objects.filter(username=username).exists():
            return Response(
                {"error": "Username already exists"}, status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(email=email).exists():
            return Response(
                {"error": "Email already exists"}, status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.create_user(
            username=username, email=email, password=password
        )
        UserProfile.objects.create(user=user)

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
                {"error": "User not authenticated"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        user_data = UserSerializer(request.user).data
        return Response({"data": {"user": user_data}})


class RefreshTokenView(APIView):
    """Custom refresh token view."""

    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get("refreshToken")

        if not refresh_token:
            return Response(
                {"error": "Refresh token is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            refresh = RefreshToken(refresh_token)
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
                {"error": "Invalid refresh token"}, status=status.HTTP_401_UNAUTHORIZED
            )


class LogoutView(APIView):
    """Logout view (invalidate token)."""

    def post(self, request):
        # For simplicity, just return success
        # In production, you would blacklist the token
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
                {"error": "Google credential is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        client_id = settings.GOOGLE_CLIENT_ID
        if not client_id:
            return Response(
                {"error": "Google OAuth is not configured on the server"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Verify the token with Google's public keys
        try:
            id_info = google_id_token.verify_oauth2_token(
                credential,
                google_requests.Request(),
                client_id,
            )
        except ValueError as exc:
            return Response(
                {"error": f"Invalid Google token: {exc}"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        email = id_info.get("email")
        email_verified = id_info.get("email_verified", False)

        if not email or not email_verified:
            return Response(
                {"error": "Google account email is not verified"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        google_name = id_info.get("name", "")
        given_name = id_info.get("given_name", "")
        picture = id_info.get("picture", "")

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
        from django.contrib.auth.models import User
        import re

        base = given_name.lower() if given_name else email.split("@")[0]
        base = re.sub(r"[^a-z0-9_]", "", base)[:20] or "user"

        candidate = base
        suffix = 1
        while User.objects.filter(username=candidate).exists():
            candidate = f"{base}{suffix}"
            suffix += 1
        return candidate
