# Auditoría del proyecto — estado a 2026-10-12

> Alcance: todo el repositorio (backend Django, frontend Angular, juego C/WASM, infraestructura
> y documentación) **después** del trabajo del módulo de póker online.
> Todo lo que aparece aquí está **verificado con ejecución real** sobre el stack desplegado
> (`docker compose up`, `https://localhost:8443`). Las herramientas para reproducirlo están en
> `scripts/audit/`.
>
> Documentos relacionados: `AUDITORIA_JUEGO_POKER.md` (auditoría del juego, ya cerrada),
> `POKER_ONLINE.md` (módulo de póker) y **`ROADMAP.md`** (plan de mejora derivado de esta auditoría).

> **Estado de las correcciones (2026-10-12)**: los tres hallazgos P0 (**A1**, **A2** y **C1**) y
> **B1** (chat roto) están **arreglados y verificados**; también los e2e caídos (E1) y parte de la
> coherencia del producto (E3) e higiene de git (F8). El detalle de cada arreglo, con la evidencia,
> está en `ROADMAP.md` (ítems marcados «✅ hecho»). Este documento describe el estado en el momento
> de la auditoría y **no** se reescribe: sirve como línea base.

---

## 1. Resumen

El proyecto está **funcional y desplegable**: los cinco contenedores levantan sanos, la app
responde por HTTPS con WAF, el póker online es autoritativo y hay 58 tests de backend en verde
(**91** tras aplicar el Bloque 0 y el 1.2 del roadmap).

Pero quedan **tres agujeros serios de integridad y privacidad**, una app rota (chat), una suite
de e2e con 2 tests caídos y una documentación que no cubre lo que la evaluación pide explícitamente.
Ninguno impide una demo; dos de ellos (A1 y C1) sí pueden costar puntos en la defensa.

| Área | Estado |
|---|---|
| Juego de póker online (motor, mesas, bots, UI) | ✅ Sólido y verificado |
| Autenticación, torneos, leaderboard, API pública, WAF/Vault | ✅ Funciona |
| Integridad de resultados | 🔴 Agujero (A1, A2) |
| Privacidad de datos de usuario | 🔴 Agujero (C1) |
| App de chat | 🔴 Rota (500) |
| Documentación de API (Swagger) | 🟡 Incompleta (19 vistas sin esquema) |
| Frontend: e2e, i18n, lobby antiguo | 🟡 2 e2e caídos, textos sin traducir, matchmaking falso |
| Tests | 🟡 4 apps sin un solo test |
| Producción (Redis, PostgreSQL, CI, observabilidad) | 🟡 Pendiente |

---

## 2. Hallazgos críticos (verificados)

### A1 — Cualquiera puede fabricarse victorias y ELO 🔴
Dos peticiones bastan:

```bash
POST /api/games/create_game/            # crea una partida contra el usuario fantasma AI_Opponent
POST /api/games/1/finish/  {"winner":"<yo>","player1_score":9999,"player2_score":0}
```

**Resultado medido:** `wins: 0 → 1`, `elo: 1600 → 1616` y el usuario aparece **nº 1 del ranking público**.

El endpoint acepta el ganador que declara el cliente y `finish_game()` actualiza ELO y balance.
El póker online ya no tiene este problema (el resultado lo escribe el servidor), pero la ruta
antigua sigue abierta.

### A2 — El resultado de un torneo lo declara el jugador 🟠
`POST /api/tournament/<id>/matches/<match>/result/` solo comprueba que quien llama sea uno de los
dos jugadores o el creador (`views.py:97-111`), pero **no verifica que el resultado sea cierto**:
cualquiera de los dos puede declararse ganador sin jugar.

### B1 — La app de chat devuelve 500 🔴
`apps/chat/views.py` usa `models.Q(...)` sin importar `models`:

```
GET  /api/chat/messages/                    -> 500 NameError at /api/chat/messages/
GET  /api/chat/messages/conversation/?user_id=1 -> 500 NameError
POST /api/chat/messages/send_message/       -> 201 (funciona porque no toca get_queryset)
```

Además: no hay ninguna interfaz de chat en el frontend, así que es una app muerta que solo aporta
un 500 al que la encuentre.

### B2 — El chat filtra direcciones de correo 🟠
`MessageSerializer` embebe `UserSerializer` completo, así que la respuesta incluye el **email** del
emisor y del receptor (`{"sender":{"email":"…"}}`). Lo mismo en la lista de mensajes.

### C1 — `GET /api/users/` expone el email de todos los usuarios 🔴
**Medido:** 6 usuarios devueltos con el campo `email`. Cualquier usuario autenticado puede
descargar la lista completa de correos. La evaluación revisa explícitamente el manejo de datos
personales, y el subject pide no exponer más información de la necesaria.

### D1 — La documentación de la API está incompleta 🟡
`manage.py check --deploy` → **57 avisos**:

| Código | Nº | Qué significa |
|---|---|---|
| `drf_spectacular.W002` | 19 | Vistas **sin esquema** en Swagger (toda `public_api`, `auth`, `leaderboard`, `health`): son `APIView` sin `serializer_class` |
| `drf_spectacular.W001` | 37 | Colisiones de `operationId` (rutas duplicadas con y sin barra final) |
| `security.W002` | 1 | Falta `XFrameOptionsMiddleware` (es intencional: el iframe del juego lo necesita, está documentado en `settings.py`) |

El módulo Major «Public API segura» exige documentación: hoy Swagger omite ~19 endpoints.

---

## 3. Frontend

### E1 — La suite e2e tiene 2 tests caídos 🟡
`npx playwright test --project=chromium` → **18 pasan, 2 fallan**:

```
✗ tournaments.spec.ts:73  opens bracket from the active tab and shows match actions
✗ tournaments.spec.ts:87  reporting a winner completes the match
   → esperan un botón /view bracket/i que ya no existe (selector obsoleto)
```

Los navegadores de Playwright están instalados y el resto de la suite pasa en 35 s.

### E2 — El i18n no está completo 🟡
El módulo Minor declara «todo el texto traducible», pero hay literales en inglés en las plantillas:
`Create your player profile`, `Enter your credentials to continue`, `Mark all read`, `Matched`,
`Players`, `REGISTER`, `TOURNAMENTS`. Y en el código: las notificaciones del torneo (`Result
reported`, `Report failed`, `Joined`, `Join Failed`, `Create Failed`), y las etiquetas
`Active`/`Upcoming`/`Finished` del bracket.

### E3 — El lobby antiguo (`/game`) sigue fingiendo matchmaking 🟡
`game-board.ts` pone el badge en `searching` y luego `matched`, y `RoomService` llama a
`/api/rooms`, `/api/rooms/<id>/join`, `/api/matchmaking/start`… **todos 404** (no existen en el
backend). El matchmaking real está ahora en `/poker`, así que esto ya no es solo código muerto:
es información engañosa en la interfaz.

### E4 — Sin tests unitarios en el frontend 🟡
Un único `app.spec.ts` (la plantilla por defecto) para 8.655 líneas de TS/HTML/SCSS. Vitest está
configurado (`@angular/build:unit-test`) pero no se usa. No hay ESLint (solo Prettier).

---

## 4. Backend y calidad

| ID | Hallazgo | Evidencia |
|---|---|---|
| F1 | Solo `tournament` (8 tests) y `poker` (58) tienen tests. **`users`, `games`, `chat` y `public_api` tienen 0** | `ls backend/apps/*/tests*` |
| F2 | Sin medición de cobertura y sin linters de Python (ni ruff, ni black, ni flake8) | `requirements.txt` |
| F3 | Cola de matchmaking y registro de mesas **en memoria del proceso**, igual que el `InMemoryChannelLayer` → no escala a más de una réplica de Daphne | `apps/poker/consumers.py`, `tables.py` |
| F4 | El despliegue usa **SQLite** (`DB_ENGINE=django.db.backends.sqlite3`) | `.env` / `compose.yaml` |
| F5 | Compose monta `./backend:/app` (código del host dentro del contenedor): cómodo en desarrollo, mala idea en producción | `compose.yaml:26` |
| F6 | **No hay CI** (`.github/workflows` no existe) | — |
| F7 | Sin observabilidad: ni logs estructurados, ni métricas, ni captura de errores | — |
| F8 | Higiene de git: `front/test-results/` (artefactos de Playwright) **no está ignorado**, `front/playwright-report/` está **versionado** y el `.gitignore` raíz apunta a `frontend/…`, una carpeta que no existe | `git check-ignore front/test-results/`, `git ls-files front/playwright-report` |

---

## 5. Juego C/WASM (`juego/`)

Ya auditado en `AUDITORIA_JUEGO_POKER.md`; lo que sigue pendiente:

| ID | Hallazgo |
|---|---|
| G1 | Los «MEJORES PUNTUACIONES» viven en el sistema de ficheros en memoria de Emscripten: **se pierden al recargar** y nunca llegan al backend |
| G2 | Código muerto: `game.h` declara `DealCardsToPlayer`, `SelectCardForPlayer` y `DeselectCardForPlayer` que **no existen** en ningún `.c`; `game_api.c` (`GamePause`/`GameRestart`/`GameSetVolume`) no se usa desde ningún sitio; `IsDealAnimationComplete` tampoco |
| G3 | El modo local no tiene IA (es hotseat) — decisión aceptada, pero conviene decirlo claro en la UI |
| G4 | `juego/DEPLOY.md` documentaba una API de embedding inexistente (ya marcada como «propuesta») |

---

## 6. Documentación

| ID | Hallazgo |
|---|---|
| H1 | El README **no tiene** las secciones que la hoja de evaluación pide explícitamente: *project management approach*, *individual contributions of each member* y los roles **PO / PM / Tech Lead** (busqué: 0 coincidencias) |
| H2 | `docs/INDEX.md` no menciona ninguno de los documentos nuevos (`AUDITORIA_*`, `POKER_ONLINE`, `ROADMAP`) |
| H3 | El README justifica el Major «Web game multijugador» como *«2-4 jugadores locales (hotseat)»*. Con el póker online esa justificación se ha quedado **corta**: el proyecto ahora sí tiene multijugador remoto real, que es lo que el subject pide |
| H4 | El README dice «Angular 21» y el `package.json` fija Angular 20 (ya detectado antes; sigue sin corregir) |

---

## 7. Lo que está bien (no tocar)

- **Póker online**: motor autoritativo, 58 tests, verificado en navegador real y en el stack desplegado.
- **Autenticación**: JWT con rotación/blacklist, Google OAuth, validación en front y back, PBKDF2.
- **Torneos**: brackets con byes y progresión, WebSocket autenticado que ignora lo que envía el cliente.
- **Infra**: Compose con TLS generado en caliente, WAF (ModSecurity/CRS) que bloquea inyección
  (403 verificado), Vault con AppRole, healthchecks y `DEBUG=false`.
- **Sin secretos versionados**: no hay `.pem`, `.key`, `.crt` ni contraseñas en el repositorio.
- **API pública**: API keys hasheadas (SHA-256), rate limiting, ≥5 recursos CRUD.
- **Juego C/WASM**: detección de manos exacta (2.598.960 manos) y comparación de póker correcta.

---

## 8. Cómo se ha verificado

```bash
# Integridad de resultados (A1)
bash scripts/audit/audit_integrity.sh          # crea usuario, se autootorga victoria, mira el ELO

# Chat roto (B1)
curl -sk -H "Authorization: Bearer $TOK" https://localhost:8443/api/chat/messages/

# Privacidad (C1)
curl -sk -H "Authorization: Bearer $TOK" https://localhost:8443/api/users/

# Documentación de API (D1)
python manage.py check --deploy

# Frontend (E1)
cd front && npx playwright test --project=chromium
```

*(los scripts exactos que usé están en `scripts/audit/`; los de esta sección se añaden en el
Bloque 0 del roadmap si quieres dejarlos automatizados)*
