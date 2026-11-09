"""Recuperar la contraseña: enlace de un solo uso por correo.

No existía nada: quien se registraba con email y olvidaba la contraseña se quedaba fuera de su
cuenta para siempre (la única salida era entrar con Google). Aquí está el token y el correo; las
vistas que lo usan viven en `auth_views.py`.

El token es el de Django (`default_token_generator`), que ya resuelve lo difícil: caduca
(`PASSWORD_RESET_TIMEOUT`, 15 minutos), deja de valer en cuanto cambia la contraseña o el
`last_login`, y no necesita tabla ni limpieza. El enlace lleva el `uid` en base64 y el token.
"""
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.translation import gettext
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken


def crear_token(user) -> tuple[str, str]:
    """(uid en base64, token) para ese usuario."""
    return urlsafe_base64_encode(force_bytes(user.pk)), default_token_generator.make_token(user)


def usuario_del_token(uidb64: str, token: str) -> User | None:
    """El usuario si el enlace es válido todavía, o None.

    Se capturan también los errores de decodificación: un `uid` manipulado no puede acabar en
    un 500.
    """
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(uidb64)))
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        return None
    return user if default_token_generator.check_token(user, token) else None


def enlace_de_reset(user) -> str:
    """La URL que se manda en el correo, apuntando a la pantalla del front."""
    uid, token = crear_token(user)
    base = settings.FRONTEND_URL.rstrip("/")
    return f"{base}/reset-password?uid={uid}&token={token}"


def enviar_correo(user) -> None:
    """Manda el enlace al correo del usuario, en el idioma de la petición."""
    enlace = enlace_de_reset(user)
    minutos = max(1, settings.PASSWORD_RESET_TIMEOUT // 60)
    asunto = gettext("Reset your Transcendence password")
    cuerpo = gettext(
        "Hi {nombre}:\n\n"
        "Someone (we hope you) asked to change the password of your account.\n"
        "The link expires in {minutos} minutes and only works once:\n\n"
        "{enlace}\n\n"
        "If it wasn't you, ignore this email: your password stays the same."
    ).format(nombre=user.username, minutos=minutos, enlace=enlace)
    send_mail(asunto, cuerpo, settings.DEFAULT_FROM_EMAIL, [user.email])


def revocar_sesiones(user) -> None:
    """Cierra todas las sesiones abiertas de ese usuario.

    Cambiar la contraseña tiene que servir también para echar a quien estuviera dentro: si no,
    un refresh robado seguiría valiendo hasta siete días después del cambio.
    """
    for emitido in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=emitido)
