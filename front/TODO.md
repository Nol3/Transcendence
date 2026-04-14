# TRANSCENDENCE — Frontend TODO

> Angular 21 · Retro Arcade Theme · ft_transcendence @42

---

## ✅ DONE

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

---

## 🔲 PENDING

### Paso 5 — Profile Page
- [ ] `/profile` — stats del jugador (wins/losses/rank/win-rate)
- [ ] Historial de partidas
- [ ] Editar avatar y username
- [ ] Formulario reactive con validación
- [ ] Conectar a `AuthService.user` signal

### Paso 6 — i18n Completo
- [ ] `i18n.service.ts` — carga dinámica de JSON, signal de idioma activo
- [ ] `TranslatePipe` — pipe `| translate` para uso en templates
- [ ] Conectar `LanguageSwitcherComponent` al servicio
- [ ] Aplicar `| translate` en todos los templates existentes
- [ ] Verificar 3 idiomas completos (EN / ES / FR)

### Paso 7 — Tournament Bracket
- [ ] `/tournament` — árbol visual de bracket (8/16 jugadores)
- [ ] Componente `BracketComponent` reutilizable
- [ ] Lista de torneos activos / próximos
- [ ] Registro a torneo
- [ ] Matchmaking UI para torneo
- [ ] Estado de partidas en tiempo real (mock → luego WebSocket)

### Paso 8 — Notificaciones en Tiempo Real
- [ ] Conectar `NotificationService` a WebSocket / SSE del backend
- [ ] Tipos: match invite, tournament start, opponent found, game result
- [ ] Persistencia de notificaciones no leídas (badge en header)
- [ ] Panel de notificaciones (dropdown o página)

### Paso 9 — API Integration
- [ ] Conectar `AuthService` al endpoint real `/api/auth/login` y `/api/auth/register`
- [ ] Conectar leaderboard a `/api/leaderboard`
- [ ] Conectar rooms a `/api/rooms`
- [ ] Conectar profile a `/api/users/:id`
- [ ] Refresh token flow en `auth.interceptor.ts`
- [ ] Environment files (`environment.ts` / `environment.prod.ts`) para base URL

---

## 📋 MÓDULOS (module points para la evaluación)

| Módulo | Tipo | Estado | Pts |
|--------|------|--------|-----|
| Frontend framework (Angular) | Minor | ✅ Done | 1 |
| Backend framework (compañero) | Minor | ⏳ Pendiente | 1 |
| Frontend + Backend framework | Major | ⏳ Pendiente (depende backend) | 2 |
| Public API (compañero/backend) | Major | ⏳ Pendiente | 2 |
| ORM (compañero/backend) | Minor | ⏳ Pendiente | 1 |
| Notification system | Minor | 🔲 Paso 8 | 1 |
| Design system 10+ componentes | Minor | ✅ Done (12) | 1 |
| i18n 3 idiomas | Minor | 🔲 Paso 6 | 1 |
| Browser compatibility | Minor | 🔲 Pendiente testing | 1 |
| WAF/Vault (Ruben) | Major | ⏳ Pendiente | 2 |
| Web-based game (compañero) | Major | ⏳ Pendiente | 2 |
| Tournament system | Minor | 🔲 Paso 7 | 1 |
| Game customization | Minor | ⏳ Pendiente | 1 |

**Total validados:** 2 pts · **Objetivo:** 14 pts mínimo

---

## 🗂 ESTRUCTURA DE CARPETAS

```
front/src/app/
├── core/
│   ├── guards/        auth.guard.ts
│   ├── interceptors/  auth.interceptor.ts
│   ├── models/        user.model.ts, api-response.model.ts
│   └── services/      api.service.ts, auth.service.ts, notification.service.ts
├── features/
│   ├── auth/
│   │   ├── login/     ✅
│   │   └── register/  ✅
│   ├── game/
│   │   ├── game-board/   ✅ (lobby + integration point)
│   │   └── tournament/   🔲 Paso 7
│   ├── home/          ✅
│   └── profile/       🔲 Paso 5
├── i18n/              en.json ✅  es.json ✅  fr.json ✅  (servicio 🔲 Paso 6)
└── shared/
    └── components/
        ├── avatar/        ✅
        ├── badge/         ✅
        ├── button/        ✅
        ├── card/          ✅
        ├── divider/       ✅
        ├── empty-state/   ✅
        ├── header/        ✅
        ├── input/         ✅
        ├── language-switcher/ ✅
        ├── modal/         ✅
        ├── pixel-title/   ✅
        ├── spinner/       ✅
        └── toast/         ✅
```

---

## 🔧 NOTAS PARA COMPAÑEROS

### Punto de integración del juego de cartas
Archivo: `src/app/features/game/game-board/game-board.html`
Busca el comentario: `<!-- Integration point: game component goes here -->`
El componente del juego va dentro de `.cabinet__screen` cuando `lobbyState() === 'idle'`.

### API base URL
Configurada en `core/services/api.service.ts` → `private readonly baseUrl = '/api'`
Cambiar a variable de entorno en Paso 9.

### Auth state
Usar `AuthService.user()` signal en cualquier componente. Es readonly y reactivo.
Usar `AuthService.isAuthenticated()` computed para guards y UI condicional.

### Notificaciones
Usar `NotificationService` inyectado:
```typescript
this.notif.success('TITLE', 'optional message');
this.notif.error('TITLE', 'optional message');
```
