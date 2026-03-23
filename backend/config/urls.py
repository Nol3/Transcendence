"""
URL Configuration for ft_transcendence project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class HealthCheckView(APIView):
    """Health check endpoint for Docker containers."""
    permission_classes = []
    authentication_classes = []
    
    def get(self, request):
        return Response({'status': 'healthy'}, status=status.HTTP_200_OK)

urlpatterns = [
    path('admin/', admin.site.urls),
    # Health check
    path('api/health/', HealthCheckView.as_view(), name='health-check'),
    # API endpoints
    path('api/users/', include('apps.users.urls', namespace='users')),
    path('api/games/', include('apps.games.urls', namespace='games')),
    path('api/chat/', include('apps.chat.urls', namespace='chat')),
    path('api/tournament/', include('apps.tournament.urls', namespace='tournament')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
