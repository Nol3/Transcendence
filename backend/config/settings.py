"""
Django settings for ft_transcendence project.
"""

from datetime import timedelta
from pathlib import Path

from decouple import Csv, config

from config.observability import logging_config
from config.vault import load_vault_secrets

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Secrets from HashiCorp Vault (empty dict when Vault is disabled/unavailable,
# in which case the `config(...)` env-var defaults below take over).
_vault = load_vault_secrets()

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = _vault.get("DJANGO_SECRET_KEY") or config(
    "DJANGO_SECRET_KEY", default="django-insecure-dev-key-change-in-production"
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config("DJANGO_DEBUG", default=True, cast=bool)

# `backend` es el nombre del servicio dentro de la red de Docker. El nginx del borde reescribe
# el `Host` con el del upstream, así que hay peticiones que llegan a Django con ese nombre; sin
# él responde 400 y, entre otras cosas, **los avatares de `/media/` no cargaban**.
ALLOWED_HOSTS = config(
    "DJANGO_ALLOWED_HOSTS", default="localhost,127.0.0.1,backend", cast=Csv()
)

# Application definition
INSTALLED_APPS = [
    "daphne",  # ASGI server for WebSockets (must precede staticfiles)
    "channels",  # WebSocket routing / consumers
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party apps
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    # Guarda los refresh revocados. Sin esta app, `BLACKLIST_AFTER_ROTATION` no hace nada:
    # SimpleJWT lo ignora en silencio y un refresh robado sigue valiendo sus 7 días.
    "rest_framework_simplejwt.token_blacklist",
    # Cabeceras de seguridad (CSP): el middleware es lo que envía la cabecera.
    "csp",
    # Local apps
    "apps.users",
    "apps.games",
    "apps.culo",
    "apps.mentiroso",
    "apps.brisca",
    "apps.tute",
    "apps.mus",
    "apps.poker",
    "apps.chat",
    "apps.tournament",
    "apps.public_api",
]

# Observabilidad (4.4): logs en JSON a stdout, con request id por petición.
LOGGING = logging_config(debug=config("DJANGO_DEBUG", default=True, cast=bool))

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Envía la cabecera Content-Security-Policy (ver CONTENT_SECURITY_POLICY más abajo).
    "csp.middleware.CSPMiddleware",
    # Lo antes posible: así todo log de la petición lleva su id.
    "config.observability.RequestIdMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # Elige el idioma de la petición a partir de la cabecera `Accept-Language`; los
    # mensajes de la API se traducen con `gettext` (roadmap 7.5).
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    # XFrameOptions removed globally — clickjacking protection now per-view via
    # @xframe_options_deny / CSP frame-ancestors. The /game/ iframe needs cross-origin
    # framing from Angular dev (:4200), which blanket DENY blocks.
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Channels layer. In-memory is enough for a single Daphne process (dev/eval).
# For horizontal scaling, switch to channels_redis.core.RedisChannelLayer.
# Con varias réplicas de Daphne el channel layer tiene que ser Redis: el de memoria
# solo ve las conexiones de su propio proceso. Se activa poniendo REDIS_URL (lo hace
# `compose.yaml`); sin ella, memoria (dev y tests, sin dependencias externas).
REDIS_URL = config("REDIS_URL", default="")

if REDIS_URL:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [REDIS_URL]},
        }
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    }

# Dónde vive la cola de emparejamiento: `redis` (compartida entre réplicas) o
# `memory` (una sola instancia). Por defecto sigue al channel layer.
MATCH_QUEUE_BACKEND = config("MATCH_QUEUE_BACKEND", default="redis" if REDIS_URL else "memory")

# Database
DB_ENGINE = config("DB_ENGINE", default="django.db.backends.sqlite3")
DB_NAME = config("DB_NAME", default=BASE_DIR / "db.sqlite3")

DATABASES = {
    "default": {
        "ENGINE": DB_ENGINE,
        "NAME": DB_NAME,
    }
}

# SQLite aguanta mucho mejor la concurrencia con WAL (varios lectores + un escritor) y
# con un tiempo de espera: sin esto, dos peticiones que escriban a la vez devuelven
# «database is locked» — se vio al correr los sondeos de auditoría en paralelo. Para
# el despliegue de verdad está PostgreSQL (ver el bloque de abajo).
if DB_ENGINE.endswith("sqlite3"):
    DATABASES["default"].setdefault("OPTIONS", {})["timeout"] = 20

    from django.db.backends.signals import connection_created

    def _sqlite_en_wal(sender, connection, **kwargs):
        """Activa WAL en cada conexión nueva (Django no tiene opción para esto)."""
        if connection.vendor == "sqlite":
            with connection.cursor() as cursor:
                cursor.execute("PRAGMA journal_mode=WAL;")

    connection_created.connect(_sqlite_en_wal, dispatch_uid="transcendence_sqlite_wal")

# Con PostgreSQL (el despliegue) hacen falta usuario, contraseña y host; SQLite
# (desarrollo y tests) no usa esas claves. `CONN_MAX_AGE` reutiliza la conexión: con
# las vistas del póker y los WebSockets, abrir una por consulta se nota.
if DB_ENGINE.endswith("postgresql"):
    DATABASES["default"].update({
        "USER": config("DB_USER", default="transcendence"),
        "PASSWORD": config("DB_PASSWORD", default=""),
        "HOST": config("DB_HOST", default="postgres"),
        "PORT": config("DB_PORT", default="5432"),
        "CONN_MAX_AGE": config("DB_CONN_MAX_AGE", default=60, cast=int),
    })

# If using PostgreSQL, uncomment and configure:
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': config('DB_NAME'),
#         'USER': config('DB_USER'),
#         'PASSWORD': config('DB_PASSWORD'),
#         'HOST': config('DB_HOST', default='localhost'),
#         'PORT': config('DB_PORT', default='5432'),
#     }
# }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
LANGUAGE_CODE = "en-us"

# Catálogos de traducción de la API (roadmap 7.5). Se compilan con
# `manage.py compilemessages` al arrancar el contenedor.
LOCALE_PATHS = [BASE_DIR / "locale"]

# Idiomas que la API sabe responder (los mismos que el front: es/en/fr).
LANGUAGES = [
    ("en", "English"),
    ("es", "Español"),
    ("fr", "Français"),
]
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Media files
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# REST Framework Configuration
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.public_api.authentication.ApiKeyAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    # nginx es el único proxy delante del backend y **añade** la IP del cliente al final de
    # `X-Forwarded-For` (`$proxy_add_x_forwarded_for`). Con NUM_PROXIES=1 DRF coge esa última
    # entrada, que es la real. Sin esto usa REMOTE_ADDR, que detrás de nginx es **siempre la
    # misma**, así que todos los anónimos del mundo compartían el límite de 60/hora (bastaba
    # con que uno lo agotara para dejar fuera a los demás). Y como nginx añade al final, un
    # `X-Forwarded-For` inventado por el cliente tampoco sirve para falsear la identidad.
    "NUM_PROXIES": 1,
    "DEFAULT_THROTTLE_RATES": {
        # Configurables por entorno: en desarrollo los e2e registran muchas cuentas y con el
        # valor de producción (que es el correcto) se quedan fuera a mitad de suite.
        "anon": config("THROTTLE_ANON", default="60/hour"),
        "user": config("THROTTLE_USER", default="1000/hour"),
        "api_key": "100/hour",
        "api_key_burst": "20/minute",
        # El login es donde se prueban contraseñas: límite propio y más estricto que el general.
        "login": config("THROTTLE_LOGIN", default="10/minute"),
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# JWT Configuration — Vault stores this under the key "JWT_SECRET".
JWT_SECRET_KEY = _vault.get("JWT_SECRET") or config(
    "JWT_SECRET_KEY", default="jwt-secret-key-change-in-production"
)
JWT_ALGORITHM = config("JWT_ALGORITHM", default="HS256")
JWT_EXPIRATION_HOURS = config("JWT_EXPIRATION_HOURS", default=24, cast=int)

# Simple JWT Configuration
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=JWT_EXPIRATION_HOURS),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": JWT_ALGORITHM,
    "SIGNING_KEY": JWT_SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
}

# CORS Configuration
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:4200,https://localhost:4200,http://127.0.0.1:4200,https://127.0.0.1:4200",
    cast=Csv(),
)
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False

# CSRF: Django exige que el origen de los POST que llegan por HTTPS esté en esta lista. Sin esto,
# con DEBUG=false el panel de administración (y cualquier formulario con sesión) da 403 en el
# dominio de verdad. En producción se pone aquí el dominio: CSRF_TRUSTED_ORIGINS=https://midominio.com
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default=(
        "http://localhost:4200,https://localhost:4200,https://localhost:8443,"
        "http://127.0.0.1:4200,https://127.0.0.1:4200"
    ),
    cast=Csv(),
)

# Email Configuration (for development, uses console backend)
EMAIL_BACKEND = config(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")

# Google OAuth2 — provisioned via env, but Vault may override it if stored there.
GOOGLE_CLIENT_ID = _vault.get("GOOGLE_CLIENT_ID") or config("GOOGLE_CLIENT_ID", default="")

# Swagger/OpenAPI Configuration
SPECTACULAR_SETTINGS = {
    "TITLE": "Transcendence API",
    "DESCRIPTION": "RESTful API for ft_transcendence card game platform",
    "VERSION": "1.0.0",
    "SERVE_PERMISSIONS": ["rest_framework.permissions.AllowAny"],
    "SERVERS": [
        {"url": "http://localhost:8000", "description": "Development"},
        {
            "url": config("PUBLIC_BASE_URL", default="https://example.com"),
            "description": "Production",
        },
    ],
    "TAGS": [
        {"name": "auth", "description": "Authentication endpoints"},
        {"name": "users", "description": "User management"},
        {"name": "games", "description": "Game records"},
        {"name": "tournaments", "description": "Tournament management"},
        {"name": "leaderboard", "description": "Rankings"},
        {"name": "public_api", "description": "Public API with API keys"},
    ],
}

APPEND_SLASH = True

# Security settings for production
if not DEBUG:
    # Nginx/ModSecurity terminates TLS and forwards X-Forwarded-Proto. Without
    # this, Django thinks every request is plain HTTP and SECURE_SSL_REDIRECT
    # would 301 forever → infinite redirect loop behind the proxy.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    # HSTS — se le dice al navegador que solo hable HTTPS. Es configurable a propósito: tanto
    # `preload` como «incluir subdominios» son difíciles de deshacer en el navegador de cada
    # visitante, así que en un dominio recién comprado se puede empezar con valores prudentes
    # (por ejemplo SECURE_HSTS_SECONDS=300) hasta comprobar que todo va por HTTPS.
    SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=31536000, cast=int)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = config(
        "SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True, cast=bool
    )
    SECURE_HSTS_PRELOAD = config("SECURE_HSTS_PRELOAD", default=True, cast=bool)
    SECURE_CONTENT_TYPE_NOSNIFF = True

# ── CSP (Content Security Policy) ────────────────────────────────────────────────
# Aquí había un `SECURE_CONTENT_SECURITY_POLICY` que **no existe en Django**: nadie lo leía y
# no se enviaba ninguna cabecera, así que daba sensación de protección sin dar ninguna. Esto
# sí lo aplica `django-csp` (middleware), y la política está ajustada a lo que la app necesita
# de verdad para no romperla:
#   · Google Sign-In (el script y el iframe del botón) y Google Fonts.
#   · `'wasm-unsafe-eval'`: el juego del módulo es WebAssembly; sin esto no compila.
#   · `style-src 'unsafe-inline'`: Angular inyecta estilos en tiempo de ejecución y el index
#     lleva el crítico en un `<style>`.
#   · El iframe del juego y los WebSocket de las salas son del mismo origen.
# Va fuera del bloque de `DEBUG` a propósito: así el e2e (que corre contra la app construida)
# también la prueba, en vez de estrenarla en producción.
_CSP_ORIGENES_DEV = ["http://localhost:4200", "http://127.0.0.1:4200"] if DEBUG else []
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": ["'self'"],
        "script-src": ["'self'", "https://accounts.google.com", "'wasm-unsafe-eval'"],
        "style-src": ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
        "font-src": ["'self'", "https://fonts.gstatic.com"],
        "img-src": ["'self'", "data:", "blob:"],
        "connect-src": ["'self'"],
        # El juego WASM va en un iframe; en desarrollo ese iframe lo sirve el backend y el
        # front puede venir de `ng serve`, de ahí los orígenes extra (solo en DEBUG).
        "frame-src": ["'self'", "https://accounts.google.com", *_CSP_ORIGENES_DEV],
        "worker-src": ["'self'"],
        "manifest-src": ["'self'"],
        "media-src": ["'self'"],
        "object-src": ["'none'"],
        "base-uri": ["'self'"],
        "frame-ancestors": ["'self'", *_CSP_ORIGENES_DEV],
        "form-action": ["'self'"],
    },
}

# Allow Google Sign-In popups to communicate with parent window
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin-allow-popups"
