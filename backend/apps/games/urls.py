"""Games app URLs."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'games'

router = DefaultRouter()
router.register(r'', views.GameViewSet, basename='game')

urlpatterns = [
    path('', include(router.urls)),
]
