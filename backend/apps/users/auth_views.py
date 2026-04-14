"""Custom authentication views compatible with frontend."""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from apps.users.serializers import UserSerializer


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
    """Get current user."""

    def get(self, request):
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
