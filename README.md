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
| Frontend | Angular 20 (standalone components, signals, reactive forms) |
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

### Roles de gestión

| Rol | Integrante | Responsabilidades |
|-----|------------|-------------------|
| Product Owner (PO) | `alcarden` (Alejandro Cárdenas) | Prioriza el backlog, decide el alcance de los módulos, valida contra el subject |
| Project Manager (PM) | `ribana-b` (Rojohn) | Planifica los sprints, sigue el tablero, coordina entregas y bloqueos |
| Tech Lead | `alcarden` (Alejandro Cárdenas) | Decide la arquitectura, revisa los PRs, marca los estándares de código |

> Los tres roles son **rotativos por hito** (ver «Gestión del proyecto»): cada miembro asume
> responsabilidades de gestión además de su área técnica. En el arranque del proyecto: **PO** y
> **Tech Lead** `alcarden`, **PM** `ribana-b`.

---

## Gestión del proyecto

**Enfoque**: desarrollo incremental por hitos con **git-flow simplificado**. Cada cambio entra por
una rama de trabajo (`feat/…`, `fix/…`) y se integra con **Pull Request revisada por otro miembro**;
`main` se mantiene siempre desplegable con `docker compose up -d`.

Evidencia en el repositorio:

- **110 commits** entre el 23/03/2026 y el 01/07/2026 (15 semanas), con picos en las semanas de
  entrega (W18: 20 commits, W23: 29).
- **28 Pull Requests** fusionados (`git log --merges`), todos con revisión de un compañero antes de
  entrar en `main`.
- Ramas con convención de nombre: `fix/tournament-creation`, `fix/avatar`,
  `fix/policies-terms-and-conditions`…
- **Despliegue reproducible**: un único `docker compose up -d` levanta backend, frontend, nginx con
  TLS y WAF, y Vault; el mismo comando funciona en local y en el servidor.
- **Calidad antes de integrar**: `backend/`: `python manage.py test` (91 tests) y
  `front/`: `npx playwright test` (e2e) más los `scripts/audit/*.sh` de verificación.

### Contribuciones individuales

Datos tomados de `git log` (autor de cada commit, 23/03/2026–01/07/2026):

| Integrante | Login 42 | Commits | Áreas principales |
|---|---|---|---|
| Alejandro Cárdenas | `alcarden` | 58 | Juego C/WASM (`juego/`), backend (póker, torneos, auth), frontend, despliegue |
| Rojohn (SrVariable) | `ribana-b` | 28 | Backend (modelos, API, WebSockets), integración del juego, docker, documentación |
| Pablo Jiménez | `pjimenez` | 17 | Backend (apps y configuración), frontend, scripts de setup |
| Rubén Egea | `regea-go` | 7 | Docker/compose, ModSecurity (WAF), HashiCorp Vault, pruebas de seguridad |

Reparto por área de código (ficheros tocados por cada autor): `juego/` y `backend/apps/` concentran
la autoría de `alcarden`; `ribana-b` y `pjimenez` se reparten `backend/` y `front/`; `regea-go` lleva
`docker/`, `docker-compose.yml`, `waf_test.sh` y `scripts/vault-init.sh`.

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
| Web game multijugador | 2 | ✅ | **Póker Texas Hold'em online y autoritativo**: cola de emparejamiento (rival humano o bot de reserva), mesa con ciegas/apuestas/fold/raise/all-in, showdown y ELO. Además, el juego de cartas C/WASM en modo local (2-4 jugadores hotseat) |

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

### Con Docker (un solo comando)
```bash
docker compose up --build
# App lista en: https://localhost:8443  (TLS + WAF; acepta el cert autofirmado)
```
El servicio `ssl-init` genera el certificado TLS autofirmado en caliente dentro de
un volumen, por lo que **no hay ninguna clave privada versionada en el repositorio**.

`docker compose up -d` levanta **seis servicios**: `backend` (Django + Daphne),
`frontend` (Angular servido por nginx), `nginx` (TLS + WAF), `postgres`, `redis` y
`vault`. Estado y salud de cada uno:

```bash
docker compose ps                    # todos en (healthy)
docker compose exec backend curl -s http://localhost:8000/api/health/
# {"status":"healthy","checks":{"db":"ok","redis":"ok"}}
```

**Despliegue (sin montar el código del host y sin `runserver`):**

```bash
docker compose -f compose.yaml -f compose.prod.yaml up -d --build
```

El overlay `compose.prod.yaml` sirve el backend con **Daphne** (ASGI: HTTP y
WebSockets), ejecuta `collectstatic` al arrancar y deja de montar `./backend:/app`,
así que el contenedor contiene exactamente lo que trae la imagen.

**Base de datos**: por defecto SQLite (cero configuración). Para usar PostgreSQL,
descomenta las líneas `DB_*` en `.env` — el servicio `postgres` ya viene en el
compose con su volumen; los datos de SQLite no se migran solos.

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

**Punto de entrada principal (evaluación):** **https://localhost:8443** — todo el
tráfico pasa por el reverse proxy Nginx con **TLS + WAF (ModSecurity)**. Acepta el
certificado autofirmado la primera vez. El frontend habla con el backend por HTTPS
mediante rutas relativas (`/api`, `wss://…/ws`), así que **todas las conexiones van
cifradas**.

| Servicio | URL |
|----------|-----|
| **App completa (HTTPS + WAF)** | **https://localhost:8443** |
| Swagger / OpenAPI | https://localhost:8443/api/docs/ |
| Admin Django | https://localhost:8443/admin/ |
| Frontend directo (sin WAF, solo dev) | http://localhost:4200 |
| Backend directo (sin WAF, solo dev) | http://localhost:8000 |

---

## Estado de módulos

**Todos los módulos declarados están implementados y son funcionales — 15 puntos
mandatory (supera el mínimo de 14).** Ver la tabla de puntuación arriba para el
mapeo exacto contra el subject.

### ✅ Major (2 pts c/u)
- **Framework frontend + backend** — Angular 20 (SPA) + Django 4.2 (DRF)
- **Public API segura** — API key (hasheada) + rate limiting + ≥5 recursos CRUD
- **WAF/ModSecurity + HashiCorp Vault** — WAF bloquea SQLi/XSS (403); Vault gestiona secretos
- **Web game multijugador** — Póker online autoritativo (cola + bots + ELO) y juego local C/WASM 2-4 jugadores

### ✅ Minor (1 pt c/u)
- **ORM** — User, UserProfile, Game, Tournament, Round, Match, APIKey
- **Design system** — 14 componentes reutilizables + tokens (SCSS)
- **Notificaciones** — ToastComponent + NotificationService
- **i18n** — EN/ES/FR con switcher en UI
- **Compatibilidad navegadores** — Chrome, Firefox, Edge (ver `front/BROWSER_COMPAT.md`)
- **Sistema de torneos** — Brackets single-elimination, registro, reporte de resultados y progresión en vivo (WebSocket)
- **Game customization** — Nº de jugadores, puntuación objetivo y tema del tapete

### ➕ Bonus
- **Google OAuth2** — Sign-in con Google (GSI + verificación de credencial)

---

## Seguridad

- Contraseñas hasheadas con PBKDF2 (Django) + JWT (SimpleJWT con rotación/blacklist)
- Google OAuth2 integrado (verificación de credencial en backend)
- API keys **almacenadas hasheadas** (SHA-256); el texto plano se muestra una sola vez
- Rate limiting (100 req/hr en API pública)
- CORS configurado + TLS terminado en el WAF (HTTPS en `:8443`)
- **WAF (ModSecurity/CRS)** bloquea SQLi/XSS y restringe métodos HTTP
- **HashiCorp Vault** (AppRole) gestiona los secretos de la app

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