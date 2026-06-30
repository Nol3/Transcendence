# TODO — Deploy Transcendence a Vercel

## Estado actual del proyecto

| Componente | Tech | Estado |
|---|---|---|
| Backend | Django 5.2 + DRF + Gunicorn | ✅ funciona local |
| Frontend | Angular 21 SSR + Express | ✅ funciona local |
| Base de datos | SQLite (dev) / PostgreSQL (prod config ready) | ⚠️ SQLite no sirve en Vercel |
| Auth | JWT custom + Google OAuth | ✅ funciona local |
| Notificaciones | SSE (Server-Sent Events) | ✅ funciona local |
| WebSockets | Rooms + matchmaking + torneos | ⚠️ NO compatible con Vercel |
| WASM Game | Raylib/Emscripten | ⚠️ `juego/web/` vacío — falta build |
| Media/Avatares | Filesystem local | ⚠️ no persiste en Vercel |

---

## Problema critico: WebSockets

Vercel es serverless — no soporta conexiones persistentes.
Los siguientes servicios del frontend usan WebSocket nativo:
- `room.service.ts` → `ws://.../ws/rooms/{id}`
- `room.service.ts` → `ws://.../ws/matchmaking`
- `tournament.service.ts` → `ws://.../ws/tournaments/{id}`

Consecuencia: el backend Django NO puede vivir en Vercel si necesitas WebSockets.

---

## Arquitectura recomendada (hibrida)

```
Vercel                     Railway (gratuito)
+-----------------+        +--------------------------+
|  Angular SSR    |------> |  Django + Daphne/Channels |
|  (frontend)     | HTTPS  |  WebSockets (/ws/*)       |
|                 |        |  SSE (/api/notifications) |
|  Archivos WASM  |        |  PostgreSQL               |
|  como estaticos |        |  Media (Cloudinary/S3)    |
+-----------------+        +--------------------------+
```

Esta es la opcion mas rapida y que "funciona perfectamente".

---

## PASO 1 — Preparar el Backend para produccion

### 1.1 Configurar PostgreSQL en Railway

1. Crear cuenta en https://railway.app
2. New Project → Deploy from GitHub repo (solo el directorio `backend/`)
3. Add Plugin → PostgreSQL → Railway crea la DB automaticamente
4. Copiar la variable `DATABASE_URL` que Railway genera

### 1.2 Variables de entorno en Railway (Settings → Variables)

```
DJANGO_SECRET_KEY=<genera uno: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())">
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=<tu-proyecto>.up.railway.app,localhost
DB_ENGINE=django.db.backends.postgresql
DB_NAME=<del DATABASE_URL de Railway>
DB_USER=<del DATABASE_URL de Railway>
DB_PASSWORD=<del DATABASE_URL de Railway>
DB_HOST=<del DATABASE_URL de Railway>
DB_PORT=5432
JWT_SECRET_KEY=<genera uno aleatorio>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
CORS_ALLOWED_ORIGINS=https://<tu-proyecto>.vercel.app
GOOGLE_CLIENT_ID=<tu Google OAuth client ID>
```

### 1.3 Cambios en `backend/config/settings.py`

Deshabilitar `CORS_ALLOW_ALL_ORIGINS` en produccion (actualmente esta `True`):

```python
# Cambiar esta linea:
CORS_ALLOW_ALL_ORIGINS = True  # SOLO dev

# Por esto:
CORS_ALLOW_ALL_ORIGINS = config("CORS_ALLOW_ALL_ORIGINS", default=False, cast=bool)
```

### 1.4 Media files — almacenamiento externo

Railway no tiene filesystem persistente entre deploys. Opciones:

Opcion A: Cloudinary (plan gratuito generoso)
```bash
pip install cloudinary django-cloudinary-storage
echo "cloudinary==1.41.0" >> backend/requirements.txt
echo "django-cloudinary-storage==0.3.0" >> backend/requirements.txt
```

```python
# settings.py — anadir:
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': config('CLOUDINARY_API_KEY'),
    'API_SECRET': config('CLOUDINARY_API_SECRET'),
}
```

Variables adicionales en Railway:
```
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
```

Opcion B: Railway Volume (requiere plan de pago, pero mas simple — no cambia el codigo)

### 1.5 Instalar `psycopg2` para PostgreSQL

```bash
pip install psycopg2-binary
echo "psycopg2-binary==2.9.10" >> backend/requirements.txt
```

### 1.6 Crear `backend/Procfile`

```
web: gunicorn --bind 0.0.0.0:$PORT --workers 4 --timeout 120 config.wsgi:application
release: python manage.py migrate --noinput && python manage.py collectstatic --noinput
```

Si implementas WebSockets (Paso 5), cambiar `web` por:
```
web: daphne -b 0.0.0.0 -p $PORT config.asgi:application
```

### 1.7 Configurar `backend/runtime.txt`

Railway necesita saber la version de Python:
```
python-3.11.x
```

### 1.8 Ejecutar migrations iniciales

Una vez Railway desplegado, desde la consola de Railway:
```bash
python manage.py migrate
python manage.py createsuperuser
```

---

## PASO 2 — Preparar el Frontend para Vercel

### 2.1 Actualizar `front/src/environments/environment.prod.ts`

```typescript
export const environment = {
  production: true,
  apiUrl: 'https://<tu-proyecto>.up.railway.app/api',
  wsUrl: 'wss://<tu-proyecto>.up.railway.app/ws',
  gameUrl: 'https://<tu-proyecto>.up.railway.app/game/',
  gameAssetsUrl: 'https://<tu-proyecto>.up.railway.app/game-assets',
  googleClientId: '<tu-google-client-id>.apps.googleusercontent.com',
};
```

Reemplazar `<tu-proyecto>` con el nombre real de tu proyecto en Railway.

### 2.2 Verificar outputMode en `angular.json`

Ejecutar:
```bash
grep -r "outputMode" front/angular.json
```

Si no aparece nada o dice `"static"`, el SSR no funciona en Vercel.
El `app.routes.server.ts` ya tiene `RenderMode.Client` para rutas dinamicas.
Para SSR real, asegurarse de que angular.json tenga la configuracion de server correcta.

### 2.3 Crear `front/vercel.json`

```json
{
  "framework": "angular",
  "buildCommand": "npm run build -- --configuration production",
  "outputDirectory": "dist/front/browser",
  "installCommand": "npm ci",
  "headers": [
    {
      "source": "/game(.*)",
      "headers": [
        { "key": "Cross-Origin-Opener-Policy", "value": "same-origin" },
        { "key": "Cross-Origin-Embedder-Policy", "value": "require-corp" },
        { "key": "Cross-Origin-Resource-Policy", "value": "cross-origin" }
      ]
    }
  ],
  "rewrites": [
    { "source": "/((?!api/).*)", "destination": "/index.html" }
  ]
}
```

NOTA: Los headers COOP/COEP son obligatorios para que el juego WASM funcione
(habilitan SharedArrayBuffer que Emscripten necesita).

### 2.4 Conectar repositorio a Vercel

1. Ir a https://vercel.com → New Project
2. Import Git Repository → seleccionar el repo
3. Root Directory: `Transcendence/front` (IMPORTANTE — solo el frontend)
4. Framework Preset: Angular
5. Build Command: `npm run build -- --configuration production`
6. Output Directory: `dist/front/browser`
7. Deploy

---

## PASO 3 — Build del juego WASM

El directorio `juego/web/` esta vacio. Sin el build, el juego no aparece.

Requisito: Emscripten SDK instalado (en WSL o Linux):

```bash
# En WSL
cd Transcendence/juego

# Instalar Emscripten si no esta
git clone https://github.com/emscripten-core/emsdk.git ~/emsdk
~/emsdk/emsdk install latest
~/emsdk/emsdk activate latest
source ~/emsdk/emsdk_env.sh

# Compilar Raylib para web
make build-raylib-web

# Compilar el juego
make web

# Verificar que existan los archivos:
ls web/
# Debe mostrar: index.html  index.js  index.wasm  index.data
```

Los archivos de `juego/web/` son servidos por Django desde `/game/`.
El backend en Railway los servira automaticamente al hacer deploy.
Hacer commit de `juego/web/` al repo antes de hacer push.

---

## PASO 4 — Google OAuth en produccion

1. Ir a https://console.cloud.google.com → Credentials → tu OAuth 2.0 Client ID
2. Authorized JavaScript origins → anadir:
   - `https://<tu-proyecto>.vercel.app`
3. Authorized redirect URIs → anadir:
   - `https://<tu-proyecto>.vercel.app`
   - `https://<tu-proyecto>.up.railway.app`
4. Copiar el Client ID → pegar en `environment.prod.ts`

---

## PASO 5 — WebSockets (para multiplayer real)

Las rutas WebSocket (`/ws/rooms/`, `/ws/matchmaking`, `/ws/tournaments/`) no estan
implementadas en el backend todavia (el codigo existe en el frontend pero Django
no tiene `channels` ni routing WebSocket).

Para implementarlas:

```bash
pip install channels
echo "channels==4.2.0" >> backend/requirements.txt
```

Crear `backend/apps/games/ws_routing.py`:
```python
from django.urls import re_path
from . import consumers  # crear consumers.py

websocket_urlpatterns = [
    re_path(r'ws/rooms/(?P<room_id>\w+)$', consumers.RoomConsumer.as_asgi()),
    re_path(r'ws/matchmaking$', consumers.MatchmakingConsumer.as_asgi()),
    re_path(r'ws/tournaments/(?P<tournament_id>\w+)$', consumers.TournamentConsumer.as_asgi()),
]
```

Actualizar `backend/config/asgi.py`:
```python
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from apps.games.ws_routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": URLRouter(websocket_urlpatterns),
})
```

Actualizar Procfile para usar Daphne:
```
web: daphne -b 0.0.0.0 -p $PORT config.asgi:application
```

---

## PASO 6 — SSE en produccion (notificaciones)

Las SSE funcionan en Railway sin cambios adicionales.
El endpoint `GET /api/notifications/sse?token=<JWT>` ya esta implementado.

En `notification.service.ts` la URL ya fue corregida a usar `environment.apiUrl`
→ apuntara al backend de Railway en produccion.

---

## PASO 7 — Checklist final antes de deploy

### Backend (Railway)
- [ ] `psycopg2-binary` en `requirements.txt`
- [ ] `Procfile` creado en `backend/`
- [ ] `runtime.txt` creado en `backend/`
- [ ] Todas las variables de entorno configuradas en Railway
- [ ] `CORS_ALLOW_ALL_ORIGINS` desactivado en prod (via variable de entorno)
- [ ] `CORS_ALLOWED_ORIGINS` apunta al dominio de Vercel
- [ ] `DJANGO_ALLOWED_HOSTS` incluye el dominio de Railway
- [ ] Media files configurados (Cloudinary u otro almacenamiento externo)
- [ ] Migrations ejecutadas en produccion
- [ ] Admin superuser creado
- [ ] WASM compilado y en `juego/web/` (commiteado al repo)

### Frontend (Vercel)
- [ ] `environment.prod.ts` con URLs reales de Railway
- [ ] `vercel.json` creado en `front/`
- [ ] `googleClientId` en `environment.prod.ts` no esta vacio
- [ ] Root directory en Vercel settings apunta a `Transcendence/front`
- [ ] Build local exitoso: `npm run build -- --configuration production`

### Google OAuth
- [ ] Dominio de Vercel en Authorized JavaScript origins
- [ ] URL de Railway en Authorized redirect URIs

### Testing post-deploy
- [ ] Login con username/password funciona
- [ ] Login con Google funciona
- [ ] Perfil carga stats (`/api/users/me/stats` → 200)
- [ ] Historial de partidas carga (`/api/users/me/history` → 200)
- [ ] Notificaciones SSE se conectan (Network → EventStream en devtools)
- [ ] Juego WASM carga en iframe (sin errores COOP/COEP en consola)
- [ ] Leaderboard muestra datos
- [ ] Upload de avatar funciona y persiste

---

## Optimizaciones aplicadas en esta sesion

### Backend
- `users/urls.py`: Anadidos endpoints correctos para el frontend:
  `/users/me/stats`, `/users/me/history`, `/users/me/update_profile`, `/users/me/upload_avatar`
  `/users/{pk}/stats`, `/users/{pk}/history`
- `views.py`: Stats retorna camelCase (`winRate`, `gamesPlayed`, `currentStreak`, `longestStreak`)
  matching exacto con el interface `UserStats` del frontend
- `views.py`: Helper `_build_stats()` y `_build_history_page()` reutilizables
  para self y para otros usuarios
- `views.py`: `playedAt` en historial (era `played_at`, frontend esperaba camelCase)
- `views.py`: Imports limpios (eliminados `Max`, `AllowAny`, serializers no usados)

### Frontend
- `user.service.ts`: Fix critico en `getUserStats()`:
  mapping incorrecto `res.data!.stats` → `res.data!`
  (backend retorna `{data: UserStats}`, no `{data: {stats: UserStats}}`)
- `notification.service.ts`: SSE URL corregida de relativa `/api/...`
  (iba al puerto 4200 de Angular) a `${environment.apiUrl}/...` (apunta al backend en 8000)
- `index.html`: Favicon cambiado de Angular "A" a logo del juego (favicon.png)

---

## Referencia de URLs

| Servicio | Local | Produccion |
|---|---|---|
| Frontend | http://localhost:4200 | https://tu-proyecto.vercel.app |
| Backend API | http://localhost:8000/api | https://tu-proyecto.up.railway.app/api |
| WebSockets | ws://localhost:8000/ws | wss://tu-proyecto.up.railway.app/ws |
| Juego WASM | http://localhost:8000/game/ | https://tu-proyecto.up.railway.app/game/ |
| Admin Django | http://localhost:8000/admin/ | https://tu-proyecto.up.railway.app/admin/ |
| Swagger docs | http://localhost:8000/api/docs/ | https://tu-proyecto.up.railway.app/api/docs/ |
