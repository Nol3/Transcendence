"""Tournament app URLs."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'tournament'

router = DefaultRouter()
router.register(r'', views.TournamentViewSet, basename='tournament')

urlpatterns = [
    path('', include(router.urls)),
]
