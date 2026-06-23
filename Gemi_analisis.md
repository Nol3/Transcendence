# Reporte de Evaluación — ft_transcendence

Este reporte documenta los hallazgos tras una auditoría exhaustiva del proyecto con respecto a la hoja de evaluación `eval_sheet.md`. El análisis se ha llevado a cabo de forma estática sobre el código base del frontend (Angular), backend (Django), contenedores (Docker / Nginx / ModSecurity / Vault) y la integración del juego (WASM).

---

## 📊 Resumen Ejecutivo

Actualmente, el proyecto **no cumple con los requisitos mínimos para aprobar la evaluación**. Aunque cuenta con una excelente base visual y de componentes custom en Angular, presenta discrepancias críticas de funcionalidad y fallos de configuración de seguridad que resultarían en un rechazo inmediato por parte de los evaluadores.

### Resumen de Cumplimiento
- **Requisitos de README.md**: ⚠️ Parcialmente completo (faltan secciones obligatorias).
- **Despliegue y Contenedores**: ✅ Configurado (ModSecurity WAF, Vault, Nginx, Django, Angular).
- **Backend / Django**: ⚠️ Funcional, pero sin tests unitarios y con configuraciones de seguridad erróneas.
- **Frontend / Angular**: ✅ Alta fidelidad visual, pero con componentes y rutas sin usar.
- **Módulos reclamados (14 pts)**: ❌ **Incompleto / No Funcional**. Varios módulos clave carecen de integración o implementación real (como WebSockets, torneo interactivo y guardado de estadísticas del juego).

---

## 🔍 Hallazgos Críticos por Categorías

### 1. Integridad del README.md (Preliminares)
La hoja de evaluación exige explícitamente secciones específicas en el `README.md`. Actualmente faltan:
- **Roles asignados** siguiendo la terminología exacta (PO, PM, Tech Lead, Developers).
- **Enfoque de gestión de proyecto** (cómo se organizó el trabajo del equipo).
- **Justificaciones de las tecnologías utilizadas**.
- **Justificaciones de los módulos seleccionados** con sus cálculos de puntos detallados.
- **Contribuciones individuales detalladas** de cada miembro del equipo.

Además, hay una **incoherencia matemática** en la tabla de puntos acumulados: el subtotal indicado es 14, pero la suma de los puntos de la lista da 13 (1 + 1 + 1 + 1 + 1 + 1 + 2 + 1 + 2 + 1 + 1 = 13).

---

### 2. Discrepancias del Sistema de Torneos (Tournament System — Minor 1 pt)
El módulo de Torneo está reclamado como completo en el README. Sin embargo, en el backend:
- No existen modelos ni tablas de base de datos para `Match` (Partidas) o `Round` (Rondas) de torneos. Solo existen `Tournament` y `TournamentParticipant`.
- No hay endpoints para iniciar un torneo, avanzar rondas, registrar resultados o generar emparejamientos en `apps/tournament/views.py`.
- En el frontend, el servicio `TournamentService` tiene hardcodeada la propiedad `rounds: []` al adaptar la respuesta del backend.
- **Impacto**: Al interactuar con el frontend, al seleccionar cualquier torneo, el usuario siempre verá la pantalla de *"Bracket will be generated when all players are registered"*, siendo imposible renderizar un bracket o avanzar el torneo. **El módulo obtendría 0 puntos.**

---

### 3. Falta de Servidor de WebSockets (Matchmaking & Rooms)
El frontend contiene servicios como `RoomService` y `TournamentService` con código que intenta abrir conexiones WebSocket a:
- `/ws/rooms/{id}`
- `/ws/matchmaking`
- `/ws/tournaments/{id}`

Sin embargo, en el backend:
- **Django Channels** no está instalado en `requirements.txt`.
- No existe el archivo de routing de WebSockets ni consumidores (ej. `consumers.py`).
- El archivo `asgi.py` tiene la configuración por defecto de Django que solo maneja HTTP.
- Además, en el frontend, el servicio `RoomService` y las llamadas a WebSockets de torneos nunca llegan a importarse ni a ejecutarse en los componentes de la interfaz.

---

### 4. Integración Unidireccional del Juego C/WASM (Game Integration)
El juego de cartas en C (compilado a WASM) se carga mediante un `<iframe>` en el frontend Angular.
- **Flujo actual**: La aplicación web envía mediante `postMessage` el nombre del usuario y el idioma al iframe del juego.
- **Problema de integración**: No existe ningún listener en el frontend ni callback de salida en el juego C/WASM para reportar el resultado de la partida (ganador, puntuación, finalización) de vuelta al contenedor web.
- **Impacto**: Jugar partidas no actualiza las estadísticas del jugador (`win_count`, `loss_count`, `elo_rating`) en la base de datos ni registra el historial de partidas, a pesar de que el backend expone la REST API para ello.

---

### 5. Configuración de Seguridad en Producción (WAF / Django)
Se detectaron fallos severos de configuración que romperían el entorno en producción (`DEBUG = False`):

> [!WARNING]
> **Bucle Infinito de Redirección (HTTPS Redirect Loop)**
> En `settings.py`, si `DEBUG = False`, se activa `SECURE_SSL_REDIRECT = True`. Sin embargo, el backend Django se ejecuta detrás del contenedor proxy Nginx y recibe las peticiones en HTTP en el puerto 8000. Al no estar configurada la variable `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')` en Django, el servidor considerará que toda petición entrante es insegura y responderá con un redirect 301 a HTTPS. Esto causa un bucle infinito en el navegador.

> [!IMPORTANT]
> **Políticas CSP Inválidas en Django**
> En `settings.py` se define `SECURE_CONTENT_SECURITY_POLICY = { "default-src": ("'self'",) }`. El middleware nativo de seguridad de Django **no soporta** esta directiva; se requiere el paquete `django-csp` (el cual no está instalado). Por ende, Django no envía cabeceras CSP.

> [!NOTE]
> **Falta de Cabeceras de Seguridad en la API**
> El archivo de configuración de Nginx para producción (`docker/waf.conf`) no incluye directivas `add_header` para HSTS, CSP, X-Frame-Options o X-Content-Type-Options. Como la configuración de Django eliminó el middleware global de clickjacking (`XFrameOptionsMiddleware`) para permitir el iframe del juego, los endpoints de la API (`/api/*`) se exponen sin protección contra clickjacking, MIME-sniffing o transporte inseguro (HSTS).

---

### 6. Calidad de Código y Cobertura de Pruebas
- **Backend Tests**: No existen tests unitarios ni de integración automatizados en el backend. Ejecutar `python backend/manage.py test` arroja `Ran 0 tests`.
- **Boilerplate en el Frontend**: Se incluyen componentes generados por defecto por Angular CLI (`componente1`, `componente2`, `componente3`) que están completamente vacíos, sin uso y sin traducción.
- **Migraciones Pendientes**: Ninguna de las migraciones de base de datos se ha aplicado sobre la base de datos local `db.sqlite3` (ejecutar `showmigrations` muestra todas las migraciones en estado `[ ]`).

---

## 🛠️ Plan de Recomendaciones / Próximos Pasos

Si el usuario lo autoriza, se proponen los siguientes cambios paso a paso para resolver estas incidencias antes de la evaluación:

### Fase 1: Correcciones de Seguridad y Estabilidad (Prioridad Alta)
1. Configurar `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')` en `backend/config/settings.py` para evitar el bucle de redirección en producción.
2. Añadir cabeceras de seguridad (`Strict-Transport-Security`, `X-Frame-Options`, `X-Content-Type-Options`) en `docker/waf.conf` para la API y rutas correspondientes.
3. Eliminar los componentes basura (`componente1`, `componente2`, `componente3`) del frontend para limpiar la estructura del código.

### Fase 2: Robustez de API y Validación de Datos (Prioridad Media)
1. Modificar `RegisterView` y `LoginView` en `backend/apps/users/auth_views.py` para que utilicen un Serializer de validación adecuado en lugar de capturar y guardar parámetros raw. Esto validará el formato de email, limitará el tamaño de campos y evitará posibles vulnerabilidades antes de tocar la DB.
2. Añadir validaciones de entrada en la acción `create_tournament` para impedir nombres vacíos/demasiado largos y garantizar que `max_players` sea un número coherente (ej. de 4 a 32).

### Fase 3: Documentación y Puntos del README (Prioridad Baja)
1. Modificar `README.md` para cubrir las secciones que exige la hoja de evaluación y corregir el cálculo de puntos.


--------------- Prompt ----------------

Hola Claude. Estoy trabajando en un proyecto de evaluación ft_transcendence (Stack: Angular 20 + Django 4.2 + SQLite/PostgreSQL + Nginx/ModSecurity + Vault).

Tengo un reporte de auditoría que identifica varios problemas críticos que impiden aprobar la evaluación. Necesito que actúes como un Ingeniero de Software Senior y realices todos los cambios necesarios en el codebase para solucionar de manera robusta y definitiva los siguientes puntos.

---

### Contexto de Archivos Clave del Proyecto
- **Frontend (Angular):** Ubicado en `/front`
- **Backend (Django):** Ubicado en `/backend`
- **Juego C/WASM:** Ubicado en `/juego`
- **Configuración Docker/Proxy:** Ubicado en `/docker` y `/compose.yaml`

Por favor, implementa las siguientes soluciones en el código:

---

### 1. Sistema de Torneos Completo (Brackets Interactivos y Progresión)
**Problema:** El backend solo tiene modelos de torneo (`Tournament` y `TournamentParticipant`) pero no define rondas ni emparejamientos. El frontend (`TournamentService`) tiene hardcodeada la propiedad `rounds: []`, por lo que el bracket nunca se genera y se queda permanentemente en "esperando jugadores".
**Solución requerida:**
1. **Modelos Django:** Crea los modelos `TournamentRound` y `TournamentMatch` (con relaciones FK a `Tournament` y `User` para los jugadores, ganador, marcador y estado de partida). Genera las migraciones correspondientes.
2. **Lógica de Torneo:** Crea una acción o señal en el backend para generar automáticamente el bracket inicial (Ronda 1) cuando el torneo se llene (`currentPlayers == maxPlayers`). Implementa la lógica para avanzar a los ganadores de ronda y finalizar el torneo.
3. **Adaptador Frontend:** Corrige el método `adapt()` en `front/src/app/core/services/tournament.service.ts` para que reciba las rondas y partidas reales del backend y las mapee al formato de la interfaz `TournamentRound` y `Match` para que `BracketComponent` renderice el bracket real de los brackets visuales.

---

### 2. Implementación de Servidor de WebSockets (Django Channels)
**Problema:** El frontend intenta conectarse a sockets en `/ws/rooms/{id}`, `/ws/matchmaking` y `/ws/tournaments/{id}`, pero el backend Django no tiene Channels configurado ni routing de WebSockets.
**Solución requerida:**
1. **Configuración backend:** Añade `channels` y `daphne` a `backend/requirements.txt`.
2. **ASGI & Routing:** Modifica `backend/config/asgi.py` para usar `ProtocolTypeRouter` y `URLRouter` con las expresiones regulares necesarias para enrutar los sockets.
3. **Consumidores:** Implementa los consumidores ASGI básicos (`RoomConsumer`, `MatchmakingConsumer` y `TournamentConsumer`) en el backend que permitan comunicar a los clientes en tiempo real.
4. **Integración frontend:** Asegúrate de que `RoomService` se importe y utilice de verdad en el flujo de juego del frontend Angular para gestionar la sala y el matchmaking en vivo.

---

### 3. Integración Bidireccional del Juego C/WASM
**Problema:** El juego de cartas compilado en C/WASM se carga mediante un `<iframe>`. El frontend envía mediante `postMessage` el nombre y lenguaje, pero el juego nunca devuelve el resultado de la partida, por lo que la base de datos no registra el historial ni actualiza el ELO/wins/losses del jugador.
**Solución requerida:**
1. **Lógica de salida en C:** En el código del juego en C (`juego/src/game.c` o archivo principal de lógica), cuando termine la partida, utiliza `emscripten_run_script()` para emitir un evento JS o enviar un `postMessage` al parent window con el resultado (`{ type: "game-finished", winner: "username", score: "..." }`).
2. **Listener en Angular:** En `front/src/app/features/game/game-board/game-board.ts`, añade un listener al evento de mensajes (`window.addEventListener('message', ...)`) que escuche `"game-finished"`.
3. **Guardar estadísticas:** Al recibir el resultado, el frontend debe realizar una petición POST al endpoint de Django `/api/games/{id}/finish/` con el ganador y los scores para actualizar el ELO y el historial del perfil del usuario.

---

### 4. Configuración de Seguridad en Producción (`DEBUG = False`)
**Problema:** Hay configuraciones que rompen producción o no cumplen los requisitos de cabeceras de seguridad.
**Solución requerida:**
1. **Bucle de redirección HTTPS:** Añade `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')` dentro del bloque `if not DEBUG:` de `backend/config/settings.py`. Esto es esencial para que Django sepa que la petición original vino por HTTPS a través de Nginx y no genere redirecciones infinitas.
2. **Cabeceras WAF/Nginx:** Añade las directivas `add_header` necesarias en `docker/waf.conf` para aplicar `Strict-Transport-Security` (HSTS), `X-Frame-Options "SAMEORIGIN"` (restríngelo adecuadamente pero permitiendo el iframe del juego en la misma URL), y `X-Content-Type-Options "nosniff"` para la ruta de la API (`/api/`).

---

### 5. Validación de Datos en Backend (Serializers)
**Problema:** Los views de autenticación (`RegisterView`) y torneos crean recursos directamente usando los parámetros recibidos sin validarlos con serializers.
**Solución requerida:**
1. **Autenticación:** En `backend/apps/users/auth_views.py`, refactora la creación de usuarios para que pase por un Serializer de Django REST Framework que valide que el email tenga el formato correcto, la contraseña cumpla con una longitud mínima de 8 caracteres y el nombre de usuario cumpla con `/^[a-zA-Z0-9_]+$/`.
2. **Torneos:** En `backend/apps/tournament/views.py`, en la acción `create_tournament`, valida la entrada usando el serializer para garantizar que `max_players` esté entre 4 y 32 y el nombre del torneo tenga un tamaño válido antes de persistirlo.

---

### 6. Limpieza de Código Muerto
**Problema:** Existen restos de plantillas generadas por defecto que ensucian la estructura.
**Solución requerida:**
1. Elimina por completo los componentes innecesarios en `/front/src/app/componente1`, `/front/src/app/componente2` y `/front/src/app/componente3`. Asegúrate de eliminar sus referencias en las pruebas o declaraciones si las hubiera.

---

Por favor, genera las modificaciones de código requeridas de forma clara y limpia, asegurando que todos los archivos queden integrados y listos para ejecutar bajo `docker compose up`.