"""Users app URLs."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'users'

router = DefaultRouter()
router.register(r'', views.UserViewSet, basename='user')

urlpatterns = [
    # /users/me/* — explicit aliases so frontend URL matches
    path('me/stats/', views.UserViewSet.as_view({'get': 'stats'})),
    path('me/history/', views.UserViewSet.as_view({'get': 'history'})),
    path('me/update_profile/', views.UserViewSet.as_view({'patch': 'update_profile'})),
    path('me/upload_avatar/', views.UserViewSet.as_view({'post': 'upload_avatar'})),
    # /users/{pk}/* — per-user stats/history for profile pages
    path('<int:pk>/stats/', views.UserViewSet.as_view({'get': 'user_stats'})),
    path('<int:pk>/history/', views.UserViewSet.as_view({'get': 'user_history'})),
    path('', include(router.urls)),
]
