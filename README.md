# ft_transcendence

*Proyecto creado como parte del currículo 42 por \<alcarden\>, \<pjimenez\>, \<ribana-b\>, \<jjaen-mo\>, \<regea-go\>.*

---

## Descripción

Aplicación web full-stack que implementa un juego de cartas competitivo con sistema de torneos, leaderboard y matchmaking en tiempo real.

### Características principales

- **Juego de cartas** — Juego de poker/azar embebido como módulo WASM con Raylib
- **Torneos** — Sistema de brackets visuales con registro y gestión de participantes
- **Autenticación** — Login/register tradicional + Google OAuth2
- **Leaderboard** — Ranking global de jugadores
- **i18n** — Soporte para inglés, español y francés
- **WebSockets** — Partidas en vivo y actualizaciones en tiempo real
- **API pública** — Endpoints con autenticación por API key

---

## Stack tecnológico

| Capa | Tecnología |
|------|------------|
| Frontend | Angular 21 (standalone components, signals, reactive forms) |
| Backend | Django 4.2 + DRF + SimpleJWT |
| Base de datos | SQLite (dev) / PostgreSQL (prod) |
| WebSockets | Daphne (ASGI) |
| Juego | C + Raylib → WASM embebido via iframe |
| Despliegue | Docker Compose + Dokploy + Traefik |

---

## Estructura del proyecto

```
Transcendence/
├── front/                 # Angular frontend
│   └── src/app/
│       ├── features/      # Login, Register, Game, Tournament, Profile
│       ├── shared/        # Button, Input, Card, Modal, Toast, Avatar...
│       ├── core/          # Services, Guards, Interceptors
│       └── i18n/          # Traducciones EN/ES/FR
├── backend/               # Django backend
│   └── api/               # REST API con JWT
├── juego/                 # Juego en C → WASM
│   └── web/               # index.html, index.js, index.wasm
├── docker/                # Dockerfiles y configuración
└── docs/                  # Documentación
```

---

## Integrantes y roles

| Rol | Integrante | Responsabilidades |
|-----|------------|-------------------|
| Frontend | alcarden, pjimenez | UI/UX, componentes Angular, diseño responsivo |
| Backend | ribana-b, jjaen-mo | API REST, autenticación, WebSockets, modelos |
| Testing & Seguridad | regea-go | WAF, pruebas, auditoría de seguridad |

---

## Endpoints principales

### Autenticación
- `POST /api/auth/login/` — Login email/password
- `POST /api/auth/register/` — Registro de usuario
- `POST /api/auth/google/` — Callback Google OAuth2
- `GET /api/auth/me/` — Usuario actual
- `POST /api/auth/refresh/` — Refrescar token JWT

### Usuarios
- `GET /api/users/` — Listar usuarios
- `GET /api/users/me/` — Perfil actual
- `PATCH /api/users/me/` — Actualizar perfil
- `GET /api/users/me/stats/` — Estadísticas (wins/losses/elo)
- `POST /api/users/me/upload_avatar/` — Subir avatar

### Juegos
- `GET /api/games/` — Listar partidas
- `POST /api/games/` — Crear partida
- `WS /ws/rooms/{id}` — WebSocket sala de juego
- `WS /ws/matchmaking` — Matchmaking en tiempo real

### Torneos
- `GET /api/tournaments/` — Listar torneos
- `POST /api/tournaments/` — Crear torneo
- `POST /api/tournaments/{id}/join/` — Registrarse
- `WS /ws/tournaments/{id}` — Actualizaciones en vivo

### Otros
- `GET /api/leaderboard/` — Ranking global (público)
- `GET /api/public/*` — API pública con API key auth

---

## Database Schema

```
User (Django built-in)
├── id (PK)
├── username (unique)
├── email (unique)
├── password (hashed)
└── profile (1:1 → UserProfile)

UserProfile
├── id (PK)
├── user_id (FK → User, 1:1)
├── avatar
├── bio
├── win_count
├── loss_count
├── elo_rating
├── is_online
└── created_at, updated_at

Game
├── id (PK)
├── player1_id (FK → User)
├── player2_id (FK → User)
├── winner_id (FK → User, nullable)
├── status (pending/in_progress/finished)
├── player1_score
├── player2_score
├── played_at
└── finished_at

Tournament
├── id (PK)
├── name
├── creator_id (FK → User)
├── winner_id (FK → User, nullable)
├── max_players
├── status (pending/in_progress/finished)
├── created_at, started_at, finished_at
├── participants (1:M → TournamentParticipant)
└── rounds (1:M → TournamentRound)

TournamentParticipant
├── id (PK)
├── tournament_id (FK → Tournament)
├── user_id (FK → User)
├── is_eliminated
├── joined_at
└── unique_together(tournament, user)

TournamentRound
├── id (PK)
├── tournament_id (FK → Tournament)
├── number, name
└── unique_together(tournament, number)

TournamentMatch
├── id (PK)
├── tournament_id (FK → Tournament)
├── round_id (FK → TournamentRound)
├── position
├── player1_id, player2_id, winner_id (FK → User, nullable)
├── player1_score, player2_score
├── status (pending/live/completed)
└── finished_at

APIKey
├── id (PK)
├── user_id (FK → User)
├── key (unique, hashed)
└── created_at
```

## Puntos acumulados (evaluación 42)

Cada módulo se mapea a un módulo del subject. **Major = 2 pts, Minor = 1 pt.**
El uso de un framework en front **y** back se cuenta **una sola vez** como el
Major "framework para frontend y backend" (no se duplica con minors de cada lado).

### Módulos Major (2 pts cada uno)

| Módulo (subject) | Pts | Estado | Justificación |
|---|---|---|---|
| Framework para frontend **y** backend | 2 | ✅ | Angular 20 (SPA) + Django 4.2 (DRF), integrados con JWT/CORS |
| Public API segura | 2 | ✅ | API key + rate limiting + docs + ≥5 endpoints (GET/POST/PUT/PATCH/DELETE) |
| WAF/ModSecurity (hardened) + HashiCorp Vault | 2 | ✅ | ModSecurity bloquea SQLi/XSS (403); Vault (AppRole) gestiona secretos |
| Web game multijugador | 2 | ✅ | Poker Race (C/WASM): **2-4 jugadores locales** (hotseat), reglas claras, victoria/derrota, stats/ELO al terminar |

### Módulos Minor (1 pt cada uno)

| Módulo (subject) | Pts | Estado | Justificación |
|---|---|---|---|
| ORM | 1 | ✅ | Django ORM: User, UserProfile, Game, Tournament, Round, Match, APIKey |
| Design system (≥10 componentes) | 1 | ✅ | 12+ componentes reutilizables + tokens de diseño (SCSS) |
| Sistema de notificaciones | 1 | ✅ | ToastComponent + NotificationService (create/update/delete) |
| i18n (≥3 idiomas) | 1 | ✅ | EN/ES/FR, switcher en UI, todo el texto traducible |
| Soporte navegadores adicionales | 1 | ✅ | Firefox + Edge testeados (ver `front/BROWSER_COMPAT.md`) |
| Sistema de torneos | 1 | ✅ | Brackets single-elimination, emparejamientos, registro y progresión |
| Game customization | 1 | ✅ | Nº de jugadores, puntuación objetivo y tema del tapete (desde la UI web) |

| **Subtotal mandatory** | **15** | ✅ | **Supera el mínimo de 14** |

### Bonus (solo si el mandatory está completo)

| Módulo | Pts | Estado | Nota |
|---|---|---|---|
| Remote auth — Google OAuth2 | +2* | ✅ | Sign-in con Google (GSI + verificación de credencial). *Confirmar clasificación exacta contra `subject.pdf`. |

**Total mandatory: 15 pts** — objetivo de 14 superado con margen. Bonus adicional con Google OAuth.

---

## Performance & Security

### API Documentation
- **Swagger/OpenAPI**: http://localhost:8000/api/docs/
- **Schema**: http://localhost:8000/api/schema/

### Security Headers
All requests are protected with:
- HSTS (Strict-Transport-Security)
- CSP (Content-Security-Policy)
- X-Frame-Options (clickjacking protection)
- X-Content-Type-Options (MIME sniffing protection)
- Permissions-Policy (feature restrictions)

### Performance Audits
```bash
# Frontend Lighthouse audit
./scripts/run-lighthouse.sh http://localhost:4200

# Backend API performance test
node scripts/backend-performance-test.js

# View results
open lighthouse-reports/lighthouse-*.html
```

See `docs/PERFORMANCE_AUDIT.md` for detailed metrics and targets.

---

## Ejecución rápida

### Con Docker
```bash
docker compose up
```

### Desarrollo local

**Backend:**
```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/WSL: source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8000
```

**Frontend:**
```bash
cd front
npm install
npm start
```

**Scripts automatizados:**
- Windows: `.\setup.ps1 -Dev`
- Linux/WSL: `./setup.sh --dev`

---

## URLs de acceso

| Servicio | URL |
|----------|-----|
| Frontend Angular | http://localhost:4200 |
| Backend Django | http://localhost:8000 |
| Juego embebido | http://localhost:8000/game/ |
| Admin Django | http://localhost:8000/admin/ |

---

## Estado de módulos

### ✅ Completados (13 pts)
- Frontend Angular 21
- Design system (Button, Input, Card, Modal, Badge, Avatar, Toast, Spinner, etc.)
- i18n con 3 idiomas
- Sistema de notificaciones en tiempo real
- Sistema de torneos con brackets
- Backend Django + DRF
- Integración Frontend ↔ Backend
- ORM con modelos User, UserProfile, Game, Tournament
- API pública con API key + rate limiting
- Google OAuth2
- **Juego de cartas** — Embedding WASM en `/game-board` via iframe (2 pts)

###  Pendientes
- **WAF + HashiCorp Vault** — Seguridad avanzada (4 pts)
- **Compatibilidad navegadores** — Firefox, Edge, Safari (1 pt)

---

## Seguridad

- JWT para autenticación
- Google OAuth2 integrado
- Rate limiting (100 req/hr en API pública)
- CORS configurado
- CSP configurable para embedding del juego
- **Planificado:** WAF (ModSecurity) + Vault para producción

---

## Notas

- El juego WASM se sirve embebido en un iframe desde `/game/`
- Durante desarrollo se relajan algunas políticas de seguridad para facilitar el embedding
- Para producción: reforzar CSP, CSRF, y proteger highscores

---

## Documentación adicional

- `docs/LOCAL_DEVELOPMENT.md` — Guía de desarrollo local
- `docs/DEVELOPMENT.md` — Notas de desarrollo
- `docs/INDEX.md` — Índice de documentación
- `juego/README.md` — Documentación del juego C/WASM