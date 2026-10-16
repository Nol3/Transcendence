"""Configuración de la app del Culo."""
from django.apps import AppConfig


class CuloConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.culo"
    verbose_name = "Culo (Presidente)"
