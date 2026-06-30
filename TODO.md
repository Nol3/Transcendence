# TODO — Auditoría de evaluación 42 (ft_transcendence)

> Auditoría inicial: 2026-06-30. **Remediación aplicada: 2026-06-30.**
>
> **Estado:** todos los puntos (🔴 CRÍTICO, 🟡 MEDIO, 🟢 BAJO) **resueltos**.
> Backend verificado (`manage.py check` limpio + 8/8 tests del torneo en verde +
> smoke test de hashing de API keys + `compose.yaml` válido). El frontend se
> revisó a nivel de tipos manualmente (no hay `node_modules` instalado en esta
> máquina, así que el `ng build` / Playwright deben ejecutarse en el entorno del
> equipo o en Docker).

---

## 🔴 CRÍTICO

- [x] **C1 — Clave privada TLS fuera de Git / generada en caliente.**
  - `compose.yaml`: nuevo servicio **`ssl-init`** (`alpine/openssl`) que genera
    `cert.pem`/`key.pem` en el volumen **`ssl_certs`** (idempotente). `nginx` ahora
    monta `ssl_certs:/etc/nginx/ssl:ro` y depende de `ssl-init`
    (`service_completed_successfully`) — ya no usa el bind mount `./docker/ssl`.
  - `.gitignore`: añadido `docker/ssl/`, `docker/ssl/*.pem`, `*.pem`, `*.key`, `*.crt`.
  - `docker/generate-ssl.sh`: robustecido (resuelve su propio dir, idempotente) como
    fallback de host.
  - ⚠️ **Pendiente del usuario (manual):** `git rm --cached docker/ssl/cert.pem docker/ssl/key.pem`.

- [x] **C2 — Frontend de torneos: WS en vivo + reporte + jugar.**
  - `tournament.service.ts`: nuevo `reportMatchResult(...)` + helper público `myUserId()`;
    `adapt()` ahora expone `creatorId`.
  - `tournament.ts`: al abrir un torneo se llama a `getTournament(id)` **y**
    `connectToTournamentUpdates(id, …)` (refresco en vivo); `ngOnDestroy`/`closeDetail`
    cierran el WS; handlers `handleReportMatch` y `handlePlayMatch`; `canManageSelected`
    (el creador arbitra).
  - **Ruta deep-link `/tournament/:id`** añadida en `app.routes.ts` (se autoselecciona).
  - `bracket.ts` + `bracket.html` + `bracket.scss`: inputs `currentUserId`/`canManage`,
    outputs `playMatch`/`reportMatch`, y sobre cada match pendiente del usuario aparecen
    **"▶ Jugar"** y botones de **ganador**.
  - `game-board.ts`: lee `?tournament=&match=&p1=&p2=`; al terminar la partida en
    contexto de torneo, reporta a
    `POST /api/tournament/{id}/matches/{matchId}/result/` y vuelve al bracket.

- [x] **C3 — README coherente (15 pts).**
  - Reescrita la sección "Estado de módulos": ya no dice "13 pts / Pendientes". Ahora
    lista Major+Minor implementados = **15 pts** + bonus Google OAuth, alineado con la
    tabla de puntuación. Sección "Seguridad" actualizada (WAF/Vault implementados).

---

## 🟡 MEDIO

- [x] **M1 — WebSocket de torneo seguro.**
  - `consumers.py`: `connect()` valida el **JWT** del query-string (`?token=`) y
    rechaza con `4401` si falta/!válido; `receive()` es ahora **no-op** (el estado solo
    lo emite el backend vía `services._broadcast`, el cliente ya no puede inyectarlo).

- [x] **M2 — `max_players` alineado.**
  - `tournament.ts`: validadores del form a `min(4)`/`max(32)` (coinciden con
    `TournamentCreateSerializer`). El `<select>` ya ofrecía 4/8/16.

- [x] **M3 — README apunta a HTTPS.**
  - Sección "URLs de acceso" y "Con Docker": **https://localhost:8443** como punto de
    entrada principal (TLS + WAF).

- [x] **M4 — Tests de backend del torneo.**
  - Nuevo `backend/apps/tournament/tests.py` (8 tests, todos en verde): generación con
    4 jugadores, byes para impares, progresión semis→final→ganador, eliminación del
    perdedor, idempotencia y guardas. Ejecutar: `python manage.py test apps.tournament.tests`.

- [x] **M5 — `join` sin condición de carrera.**
  - `views.py`: el chequeo de aforo + alta del participante van dentro de
    `transaction.atomic()` con `Tournament.objects.select_for_update()` (lock de fila;
    no se puede superar `max_players` con joins concurrentes).

---

## 🟢 BAJO

- [x] **B1 — API keys hasheadas (SHA-256).**
  - `models.py`: se almacena solo el hash; `create_for_user()` devuelve el texto plano
    una sola vez (`plain_key`). `authentication.py` busca por `hash_key(raw)`.
    `serializers.py` (`ApiKeyResponseSerializer.key`) sirve el plano transitorio.
    Verificado: el raw nunca queda en BD y el lookup por hash autentica.

- [x] **B2 — WAF: `/game/` → `/game-embed/`.**
  - `docker/waf.conf`: corregida la `location` a la ruta real del juego.

- [x] **B3 — e2e de torneo más completos.**
  - `helpers.ts`: nuevo `mockTournamentFlow` (torneo in-progress + detalle + POST de
    resultado). `tournaments.spec.ts`: 3 tests nuevos (abrir bracket + acciones,
    reportar ganador → match completado, deep-link `/tournament/:id`).

- [x] **B4 — Limpieza de raíz.**
  - Movidos a `docs/archive/`: `docker-compose.yml.backup`, `Gemi_analisis.md`,
    `Errors.md`, `TODO_TEST.md`, `launch_setup-docker.txt`, `modulos.txt` (nada borrado).

---

## Acciones manuales pendientes (usuario)

1. `git rm --cached docker/ssl/cert.pem docker/ssl/key.pem` (y commitear el borrado).
2. Instalar deps del front y validar: `cd front && npm ci && npm run build && npm run test:e2e`.
3. Levantar y probar el flujo completo: `docker compose up --build` → https://localhost:8443.
