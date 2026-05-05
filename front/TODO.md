# TRANSCENDENCE — Frontend TODO

> Angular 21 · Retro Arcade Theme · ft_transcendence @42

---

## ✅ COMPLETADO

### Paso 1 — Estructura + Design System Base
- [x] `styles.scss` — tokens CSS: colores neon, tipografía (Press Start 2P / Inter / JetBrains Mono), spacing, glows, animaciones, scanlines CRT, vignette
- [x] `index.html` — Google Fonts
- [x] `core/models/` — `user.model.ts`, `api-response.model.ts`
- [x] `core/services/` — `api.service.ts`, `auth.service.ts`, `notification.service.ts`
- [x] `core/guards/` — `auth.guard.ts` (authGuard + guestGuard)
- [x] `core/interceptors/` — `auth.interceptor.ts` (JWT Bearer + 401 auto-logout)
- [x] `app.config.ts` — HttpClient + interceptor registrado
- [x] `app.routes.ts` — lazy loading en todas las rutas
- [x] App shell — scanlines + vignette + header + toast outlet
- [x] Header — sticky glassmorphism, nav desktop + mobile hamburger, auth state reactivo
- [x] `i18n/` — `en.json`, `es.json`, `fr.json` (estructura completa)
- [x] Feature stubs — home, login, register, game-board, tournament, profile

### Paso 2 — Design System (12 componentes reutilizables)
- [x] `ButtonComponent` — 5 variantes, 3 tamaños, loading state
- [x] `SpinnerComponent` — 3 tamaños, neon cyan
- [x] `InputComponent` — ControlValueAccessor, password toggle, error/hint
- [x] `BadgeComponent` — 5 variantes con glow
- [x] `AvatarComponent` — imagen + fallback initials, 4 tamaños
- [x] `ModalComponent` — overlay backdrop blur, ESC key, content projection
- [x] `ToastComponent` — conectado a NotificationService, auto-dismiss
- [x] `CardComponent` — arcade panel, header divider neon
- [x] `DividerComponent` — 3 colores, label opcional
- [x] `EmptyStateComponent` — icono + animación pulse
- [x] `PixelTitleComponent` — H1/H2/H3, 4 colores neon, flicker mode
- [x] `LanguageSwitcherComponent` — dropdown EN/ES/FR integrado en header
- [x] Barrel export `shared/components/index.ts`

### Paso 3 — Auth Pages
- [x] `/login` — reactive form, validación (required/email/minLength), error banner, conectado a AuthService → toast + redirect
- [x] `/register` — reactive form, cross-field validator `passwordsMatch`, validación completa (username pattern, maxLength), conectado a AuthService

### Paso 4 — Home + Game Lobby
- [x] `/` Home — hero con grid perspectiva + ambient glows, reloj en tiempo real, stats bar, leaderboard mock, how-to-play, CTA contextual (auth vs guest), player status card
- [x] `/game` Game Lobby — arcade cabinet estilo físico (luces, pantalla CRT, controles), 3 estados (idle / searching / found), lista de salas, reglas, stats jugador
- [x] Punto de integración marcado para compañero del juego de cartas

### Paso 5 — Profile Page ✅
- [x] `/profile` — stats del jugador (wins/losses/rank/win-rate)
- [x] Historial de partidas
- [x] Editar avatar y username
- [x] Formulario reactive con validación
- [x] Conectar a `AuthService.user` signal
- [x] Logros del jugador

### Paso 6 — i18n Completo ✅
- [x] `i18n.service.ts` — carga dinámica de JSON, signal de idioma activo
- [x] `TranslatePipe` — pipe `| translate` para uso en templates
- [x] Conectar `LanguageSwitcherComponent` al servicio
- [x] Archivos JSON completos en `public/i18n/` (EN / ES / FR)
- [x] Inicialización asíncrona con APP_INITIALIZER

### Paso 7 — Tournament Bracket ✅
- [x] `/tournament` — árbol visual de bracket (8/16 jugadores)
- [x] Componente `BracketComponent` reutilizable
- [x] Lista de torneos activos / próximos / finalizados
- [x] Registro a torneo (modal)
- [x] Vista de bracket con matches y puntuación
- [x] Estados: pending, live, completed

### Paso 8 — Notificaciones en Tiempo Real ✅
- [x] `NotificationService` con soporte SSE
- [x] Tipos: match invite, tournament start, opponent found, game result
- [x] Badge de notificaciones no leídas en header
- [x] Panel de notificaciones con mark as read / delete
- [x] Conexión automática al autenticar

### Paso 9 — API Integration ✅
- [x] Environment files (`environment.ts` / `environment.prod.ts`) para base URL configurable
- [x] `ApiService` actualizado con environment
- [x] `AuthService` conectado a endpoints reales: `/auth/login`, `/auth/register`, `/auth/me`, `/auth/refresh`
- [x] `refreshToken()` flow en AuthService
- [x] `auth.interceptor.ts` con refresh token automatico en 401
- [x] `UserService` con: `/leaderboard`, `/users/:id`, `/users/me/stats`, `/users/me/history`
- [x] `RoomService` con: `/rooms`, WebSocket support para real-time
- [x] `TournamentService` con: `/tournaments`, WebSocket support
- [x] Profile page conectado a `UserService.getUserStats()` y `getUserHistory()`
- [x] Home leaderboard conectado a `UserService.getLeaderboard()`

### Paso 10 — Browser Compatibility ✅ (Minor - 1 pt)
- [x] Testing en Chrome (funciona correctamente)
- [ ] Testing en Firefox
- [ ] Testing en Edge/Safari
- [ ] Documentar limitaciones específicas de navegador

### Paso 11 — Privacy Policy & Terms of Service ✅ (Requisito obligatorio)
- [x] Crear página `/privacy` con política de privacidad completa
- [x] Crear página `/terms` con términos de servicio
- [x] Links en footer de la aplicación
- [x] Contenido relevante (no placeholder)
- [x] Traducciones completas (EN/ES/FR)

### Paso 12 — Game Integration (Web-based game) ⚠️ (Major - 2 pts) [COMPAÑERO]
- [ ] Implementar juego de cartas completo en `game-board`
- [ ] Matchmaking en tiempo real
- [ ] Reglas claras y condiciones de victoria/derrota
- [ ] Sistema de puntuación

### Paso 13 — Game Customization ⚠️ (Minor - 1 pt) [COMPAÑERO]
- [ ] Opciones de personalización del juego (tema, avatares, etc.)
- [ ] Configuración de preferencias del jugador

---

## 📊 PUNTUACIÓN MÓDULOS

### Módulos Validados (Frontend): 6 pts
| Módulo | Tipo | Estado | Pts |
|--------|------|--------|-----|
| Frontend framework (Angular) | Minor | ✅ Done | 1 |
| Design system 10+ componentes | Minor | ✅ Done (12) | 1 |
| i18n 3 idiomas | Minor | ✅ Done | 1 |
| Notification system | Minor | ✅ Done | 1 |
| Tournament system | Minor | ✅ Done | 1 |
| Browser compatibility | Minor | ⚠️ Parcial | 1 |

### Módulos Implementados (Backend): 4 pts
| Módulo | Tipo | Estado | Pts |
|--------|------|--------|-----|
| Backend framework (Django) | Minor | ✅ Done | 1 |
| Frontend + Backend framework | Major | ✅ Done | 2 |
| ORM (Django ORM) | Minor | ✅ Done | 1 |

### Módulos Pendientes: 6+ pts
| Módulo | Tipo | Estado | Pts |
|--------|------|--------|-----|
| Public API (5+ endpoints) | Major | ⚠️ COMPAÑERO | 2 |
| Web-based game | Major | ⚠️ COMPAÑERO | 2 |
| Game customization | Minor | ⚠️ COMPAÑERO | 1 |
| WAF/Vault (Ruben) | Major | ⚠️ RUBEN | 2 |

**Objetivo mínimo:** 14 pts | **Actual:** ~10 pts (Backend + Frontend)

---

## 🔧 NOTAS PARA COMPAÑEROS

### Backend (Alejandro)
El backend está corriendo en `http://localhost:8000` con:
- Django + Django REST Framework
- JWT Authentication (simplejwt)
- SQLite para desarrollo

**Endpoints implementados:**
- `POST /api/auth/login/` - Login con JWT
- `POST /api/auth/refresh/` - Refrescar token
- `GET /api/leaderboard/` - Leaderboard público
- `GET /api/users/me/` - Usuario actual
- `GET /api/users/me/stats/` - Stats del usuario
- `GET /api/users/me/history/` - Historial de partidas

**Usuarios de prueba:**
- player1 / password123
- player2 / password123
- player3 / password123
- player4 / password123
- player5 / password123

### Punto de integración del juego de cartas
Archivo: `src/app/features/game/game-board/game-board.html`
Busca el comentario: `<!-- Integration point: game component goes here -->`
El componente del juego va dentro de `.cabinet__screen` cuando `lobbyState() === 'playing'`.

### API base URL
Configurada en `environments/environment.ts`:
- Dev: `http://localhost:8000/api`
- Prod: `/api`

### Auth state
Usar `AuthService.user()` signal en cualquier componente. Es readonly y reactivo.
Usar `AuthService.isAuthenticated()` computed para guards y UI condicional.

### Notificaciones
Usar `NotificationService` inyectado:
```typescript
this.notif.success('TITLE', 'optional message');
this.notif.error('TITLE', 'optional message');
```

### i18n
Usar `I18nService`:
```typescript
const currentLang = this.i18n.currentLang(); // 'en' | 'es' | 'fr'
const translated = this.i18n.t('auth.login.title');
this.i18n.setLang('es'); // cambiar idioma
```

### Endpoints del Backend esperados
El frontend está preparado para conectarse a estos endpoints:

**Auth:**
- `POST /api/auth/login` → `{ user, tokens }`
- `POST /api/auth/register` → `{ user, tokens }`
- `POST /api/auth/refresh` → `{ tokens }`
- `POST /api/auth/logout` → `{}`
- `GET /api/auth/me` → `{ user }`

**Users:**
- `GET /api/leaderboard` → paginated
- `GET /api/users/:id` → `{ user }`
- `GET /api/users/me/stats` → `{ stats }`
- `GET /api/users/me/history` → paginated
- `PATCH /api/users/me` → `{ user }`
- `POST /api/users/me/upload_avatar` → `{ avatarUrl }`

**Rooms:**
- `GET /api/rooms` → paginated
- `GET /api/rooms/:id` → `{ room }`
- `POST /api/rooms` → `{ room }`
- `POST /api/rooms/:id/join` → `{ room }`
- `POST /api/rooms/:id/leave` → `{}`
- `POST /api/rooms/:id/start` → `{}`

**Tournaments:**
- `GET /api/tournaments` → paginated
- `GET /api/tournaments/:id` → `{ tournament }`
- `POST /api/tournaments` → `{ tournament }`
- `POST /api/tournaments/:id/register` → `{ tournament }`
- `POST /api/tournaments/:id/unregister` → `{}`

**WebSocket:**
- `/ws/rooms/:id?token=...` — updates de sala
- `/ws/matchmaking?token=...` — match found
- `/ws/tournaments/:id?token=...` — updates de torneo
- `/api/notifications/sse?token=...` — notificaciones SSE

---

## 🗂 ESTRUCTURA DE CARPETAS

```
front/src/app/
├── core/
│   ├── guards/        auth.guard.ts
│   ├── interceptors/  auth.interceptor.ts (con refresh token)
│   ├── models/        user.model.ts, api-response.model.ts
│   └── services/
│       ├── api.service.ts ✅ (con environment)
│       ├── auth.service.ts ✅ (con refresh token)
│       ├── notification.service.ts ✅ (con SSE)
│       ├── user.service.ts ✅ (nuevo)
│       ├── room.service.ts ✅ (nuevo, WebSocket)
│       └── tournament.service.ts ✅ (nuevo, WebSocket)
├── features/
│   ├── auth/
│   │   ├── login/     ✅
│   │   └── register/  ✅
│   ├── game/
│   │   ├── game-board/   ✅ (lobby + integration point)
│   │   └── tournament/   ✅ (bracket + registro)
│   ├── home/          ✅ (conectado a API)
│   ├── profile/       ✅ (conectado a API)
│   └── legal/         ✅ (privacy + terms)
├── i18n/              i18n.service.ts ✅  translate.pipe.ts ✅
│                       public/i18n/en.json ✅  es.json ✅  fr.json ✅
└── shared/
    └── components/
        ├── avatar/        ✅
        ├── badge/         ✅
        ├── button/        ✅
        ├── card/          ✅
        ├── divider/       ✅
        ├── empty-state/   ✅
        ├── footer/        ✅ (con links legales)
        ├── header/        ✅ (con notificaciones)
        ├── input/         ✅
        ├── language-switcher/ ✅ (conectado a i18n service)
        ├── modal/         ✅
        ├── pixel-title/   ✅
        ├── spinner/       ✅
        └── toast/         ✅

front/src/environments/
├── environment.ts      ✅ (dev)
└── environment.prod.ts ✅ (prod)
```
