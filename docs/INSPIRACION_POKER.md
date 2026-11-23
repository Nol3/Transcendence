# Inspiración para el póker: patrones, fichas de integración y plan por tandas

Fecha: 23-11-2026. Este documento convierte la investigación sobre plataformas de póker y juegos
de cartas en **trabajo integrable**: cada idea tiene referente, sitio del código, criterios de
aceptación y cómo verificarla. No es una lista de deseos.

**Cómo leerlo**

- **Hecho** = ya está en el repositorio y verificado.
- **Siguiente** = diseñado y listo para implementar; no hay código todavía.
- **Explorar** = la idea es buena, pero depende de una decisión de producto o de una pieza que
  aún no existe.
- Esfuerzo: **S** ≤ 1 tanda corta, **M** 1-2 tandas, **L** más de 2 o toca servidor y datos.

Fuentes: al final. Lo que lleva URL está descrito en fuentes públicas del producto; lo que no,
es recomendación propia. Enlaces comprobados el 23-11-2026.

---

## 0. En una página

El proyecto ya tiene lo caro: mesas autoritativas por WebSocket, cola, torneos, historial con
replay, logros, ELO, espectadores, i18n y PWA. Lo que falta no es infraestructura, es **producto
alrededor de la mesa**:

1. **Entrar en menos de 60 s.** Quick seat desde la home, sin pasar por ajustes. *(Hecho)*
2. **No perder manos por mirar a otro lado.** Aviso sonoro de turno, barra de tiempo visible.
   *(Hecho)*
3. **Decidir mejor.** Presets de apuesta, cuota del bote al igualar, y más adelante revisión
   post-mano. *(Presets y cuota: hechos)*
4. **Volver mañana.** Racha de login, misión diaria y recompensa cosmética; sin monedero no tiene
   sentido hablar de fichas. *(Siguiente)*
5. **Jugar con amigos.** Clubes/mesas privadas con código, que en las cartas españolas ya existen
   pero el póker no tiene. *(Siguiente/Explorar)*
6. **Presumir.** Tarjeta de resultado compartible. *(Hecho)*

Tres apuestas grandes, por orden: **clubes privados de póker**, **revisión post-mano** y
**fast-fold**. Las tres cambian el producto; el resto lo pule.

---

## 1. Estado de partida: qué hay y qué no

| Pieza | Estado | Dónde vive |
|---|---|---|
| Mesa autoritativa, turnos, reloj de 20 s | Hecho | `backend/apps/poker/{tables,consumers}.py` |
| Cola con emparejamiento y bot de reserva | Hecho | `backend/apps/poker/queue.py` |
| Lobby con ciegas, tamaño y temas | Hecho | `front/src/app/features/poker/` |
| Presets de subida ½, bote, 2× | Hecho | `poker.html` + `quickRaise()` |
| Presets ⅓ y ¾, cuota del bote | Hecho (23-11) | `poker.html`, `poker.ts` |
| Reloj numérico de turno | Hecho | `poker.service.armTurnClock()` |
| Barra visual del reloj | Hecho (23-11) | `poker.scss` |
| Chat de mesa | Hecho | `TableConsumer` + `poker.html` |
| Espectadores | Hecho | `TableConsumer` (sin asiento) |
| Historial + replay + logros | Hecho | `apps/poker/achievements.py`, `poker/history/` |
| Torneos con bracket | Hecho | `apps/tournament/` |
| Quick seat desde la home | Hecho (23-11) | `home.ts` → `/poker?quick=1` |
| Revancha al terminar | Hecho (23-11) | `poker.ts` + `match-over__actions` |
| Emoticonos rápidos | Hecho (23-11) | `poker.html` + `.emotes` |
| Tarjeta de resultado PNG | Hecho (23-11) | `shareResult()` (canvas + Web Share) |
| Ajuste de movimiento reducido | Hecho (23-11) | `MotionService` + clase `.reduce-motion` |
| Racha/misión diaria | Racha de login: hecha (23-11); misión: no | `UserProfile.login_streak`, `/api/users/me/checkin/` |
| Clubes privados de póker | No (sí en `apps/salas/` para cartas españolas) | — |
| Fast-fold | No | — |
| Revisión post-mano | No | — |

---

## 2. Referentes: qué copiar de cada uno

| Referente | Lo que hace bien | Patrón concreto | Dónde encaja aquí |
|---|---|---|---|
| **PokerStars** | Entrada sin fricción y retención | Quick Seat; filtros/favoritos; misiones diarias con opt-in; escuela Learn; Home Games | Quick seat, filtros de mesas, misiones, escuela |
| **GGPoker** | Mesa y seguridad | Smart Betting (sugiere tamaño), presets 33/50/75/100 %, Time Bank, Rabbit Hunt, Run It Twice, alias anónimos | Presets, time bank, rabbit hunt, anti-colusión |
| **888poker** | Juego rápido en móvil | SNAP fast-fold; “fold, watch and play”; multi-mesa ×4 con ventana que emerge | Fold & watch, fast-fold |
| **WPT Global** | Confianza como producto | FairGame (límite de pros por mesa), AceGuardian, QuintAce (revisión de manos), sin HUDs | Revisión post-mano, RNG/anti-colusión |
| **WSOP.com** | Lobby de torneos | Vista lista con bote medio y manos/hora; ficha de torneo con estructura y late reg | Ficha de torneo, filtros |
| **ClubGG** | Juego privado | Club con ID de 6 dígitos, reglas por mesa, sin rake, estadísticas | Clubes privados, estadísticas |
| **PokerBros** | Hábito y comunidad | Racha de login con bonus creciente, ruleta diaria, avatares/throwables, uniones de clubes | Racha, cosméticos, clubs |
| **Board Game Arena** | Turnos y competición | Modo asíncrono (24 h/jugada), reloj con recarga, ligas por temporadas, XP que no se pierde | Modo asíncrono, ligas |
| **Colonist.io** | Ranked y reenganche | 10 placements, temporadas de 3 meses con soft reset, “Shuffle” semanal | Temporadas, variante rotativa |
| **Chess.com** | Post-partida | Game Review con accuracy, clasificación de jugadas, revancha de un clic | Revisión post-mano, revancha |
| **Zynga / Governor of Poker 3** | Economía free-to-play | Bonus periódico, torneos Sit-N-Go, mapa de progresión, emotes, mesas privadas | Racha, emotes, mesas privadas |
| **Balatro** | “Game feel” | Cascada de puntuación, SFX que suben de tono, partículas, ajustes de velocidad y reduced motion | Juice del bote, accesibilidad |
| **Marvel Snap** | Partidas cortas y tono | 3-6 min, snap como doblar, “Escaped!” al retirarse | Reencuadre del retiro, ritmo |
| **Duolingo** | Onboarding | Primera lección antes de crear cuenta, meta y barra de progreso | Jugar contra bots sin cuenta (explorar) |
| **Discord** | Comunidad | Bot con resultados, roles por rango, canales LFG | Bot de comunidad (explorar) |

---

## 3. Los patrones que de verdad mueven la aguja

1. **La primera carta manda.** Todo lo que haya entre abrir la web y ver una mesa es deuda. Quick
   seat es la versión de póker de “primera lección antes del registro”.
2. **El reloj es una mecánica, no un adorno.** Si el jugador no sabe cuánto queda, juega peor y se
   enfada. Número + barra + sonido cubren vista, oído y tacto.
3. **Decidir el tamaño es la mitad del póker.** El slider solo es lento; los presets convierten una
   decisión en un toque.
4. **La cuota convierte una cifra en una decisión.** “Igualar 40” no dice nada; “25 %” sí.
5. **El retiro no es una derrota.** Reencuadrarlo (“¡Escapaste!”) baja la fricción emocional y
   anima a jugar la siguiente mano.
6. **El resultado se comparte.** Una imagen vale más que un log; es publicidad gratuita.
7. **La retención sin dinero real es hábito + estatus.** Racha, misión, cosmético y liga; nunca
   presión con temporizador.
8. **Jugar con amigos es el modo natural de estas cartas.** Un código de 4-6 caracteres vale más
   que cualquier matchmaking.
9. **La revisión post-mano es el diferenciador.** Un cliente que te explica la decisión cara se
   queda; uno que solo reparte, no.
10. **El “juice” se nota en la salida, no en la entrada.** Bote que cuenta, sonido que sube, carta
    que pesa. Corto (<300 ms) y con opción de reducirlo.

---

## 4. Fichas de integración

### Tanda 1 — Quick wins (hechos el 23-11-2026)

#### I-01 · Quick seat desde la home · Hecho · S
- **Referente**: PokerStars Quick Seat.
- **Problema**: el botón “Póker” llevaba al lobby, donde hay que elegir ciegas, tamaño y tema
  antes de jugar.
- **Qué se hizo**: la home navega a `/poker?quick=1`; el componente espera a que carguen las
  preferencias guardadas y entra directo a la cola. Si las preferencias fallan, entra igual con
  las de casa. El lobby sigue disponible para elegir a mano.
- **Dónde**: `features/home/home.ts` (`playNow()`), `features/poker/poker.ts`
  (`applyRoute`), `core/services/poker.service.ts` (`loadPreferences(alCargar)`).
- **Hecho cuando**: desde la home autenticada, un clic deja al jugador en “buscando” sin tocar
  ningún ajuste; cancelar vuelve al lobby normal.
- **Riesgo**: que la URL `?quick=1` se reutilice al volver atrás y re-encole sola. Mitigado con el
  guard `status() === 'idle'`.

#### I-02 · Revancha al terminar · Hecho · S
- **Referente**: Chess.com (revancha en el popup de fin).
- **Qué se hizo**: en mesas normales (no torneo) el fin de partida ofrece **Revancha**, que
  reutiliza `startQueue()` con la misma configuración; “Volver a la cola” sigue ahí como opción
  secundaria.
- **Dónde**: `poker.html` (`.match-over__actions`), `poker.ts` (`rematch()`), i18n
  `poker.table.rematch`.
- **Hecho cuando**: tras una partida terminada, Revancha deja al jugador en cola sin pasar por el
  lobby y sin errores de WebSocket.
- **Riesgo**: doble conexión si el cierre de la mesa tarda. `startQueue()` ya llama a `reset()`,
  que cierra la mesa antes de abrir la cola.

#### I-03 · Barra visual del reloj · Hecho · S
- **Referente**: GGPoker time bank.
- **Qué se hizo**: bajo el número de segundos, una barra de 4 px que se vacía con el turno y pasa
  a rojo en los últimos 5 s. Respeta `prefers-reduced-motion` (sin transición).
- **Dónde**: `poker.html`, `poker.ts` (`turnFraction`), `poker.scss` (`.turn-clock__bar`).
- **Hecho cuando**: al empezar tu turno la barra está llena y baja de forma lineal; en móvil no
  empuja el resto de la barra superior.
- **Riesgo**: si `turn_timeout` cambia a mitad de mano, la fracción se recalcula con el valor
  nuevo; es aceptable porque el servidor manda.

#### I-04 · Emoticonos rápidos · Hecho · S
- **Referente**: Governor of Poker 3; PokerBros (throwables).
- **Qué se hizo**: seis botones (👍 😂 😱 🔥 👏 💀) sobre el campo de chat. Envían el emoji como
  mensaje normal, así que no hace falta backend nuevo ni moderación extra.
- **Dónde**: `poker.html` (`.emotes`), `poker.ts` (`emotes`, `sendEmote()`), i18n
  `poker.chat.emotes`.
- **Hecho cuando**: un toque aparece en el chat de todos (jugadores y espectadores) y no abre el
  teclado en móvil.
- **Riesgo**: spam. El `TableConsumer` ya limita a 200 caracteres y 0,5 s entre mensajes; si se
  convierte en problema, se añade cooldown propio para emotes.

#### I-05 · Tarjeta de resultado compartible · Hecho · S
- **Referente**: Zynga/Discord (compartir resultado); Marvel Snap (tarjeta de fin).
- **Qué se hizo**: botón **Compartir resultado** que dibuja un PNG de 1200×630 en canvas (sin
  dependencias) con título, resultado, bote, ganancia neta, mano y ciegas. Usa Web Share si el
  navegador acepta ficheros; si no, descarga el PNG.
- **Dónde**: `poker.ts` (`shareResult()`), `poker.html` (dentro de `.outcome`), i18n
  `poker.result.share`.
- **Hecho cuando**: en escritorio descarga `transcendence-poker.png`; en móvil abre la hoja de
  compartir; cancelar no rompe nada.
- **Riesgo**: fuentes del sistema distintas por SO. Se usa `Courier New` con fallback `monospace`,
  que existe en Windows, macOS, Linux y Android.

#### I-06 · Reencuadre del retiro · Hecho · S
- **Referente**: Marvel Snap (“Escaped!”).
- **Qué se hizo**: `poker.result.lostFold` pasa de “TE RETIRAS” a **“¡ESCAPASTE!”** (EN “YOU
  ESCAPED!”, FR “ÉCHAPPÉ !”). El hecho es el mismo; cambia la lectura emocional.
- **Dónde**: `front/public/i18n/{es,en,fr}.json`.
- **Hecho cuando**: al retirarse, el título no culpabiliza y la pantalla sigue ofreciendo la
  siguiente mano.
- **Riesgo**: en una mano donde el jugador se retira tras invertir mucho, “escapaste” puede sonar
  irónico. Si molesta, se cambia a “FUERA DE LA MANO”, que es neutro.

---

### Tanda 2 — Retención y accesibilidad (siguiente)

#### I-07 · Ajuste de movimiento y velocidad · Hecho (23-11) · M
- **Referente**: Balatro (Game Speed 0,5×-4× y Reduced Motion).
- **Qué se hizo**: preferencia “Reducir animaciones” en el perfil, guardada en `localStorage` y
  aplicada como clase `reduce-motion` en `<html>` al arrancar. Por defecto se sigue respetando
  `prefers-reduced-motion`; el ajuste manual lo fuerza aunque el SO no lo pida. El CSS global
  corta animaciones y transiciones, pero deja girando el spinner para que una carga no parezca
  rota.
- **Dónde**: `core/ui/motion.service.ts`, `app.ts`, `features/profile/` (tarjeta de
  Accesibilidad), `styles.scss`.
- **Hecho cuando**: activarlo desactiva tilt de cartas, rebotes y transiciones; el cambio se
  recuerda entre sesiones y se aplica sin recargar.
- **Riesgo**: la regla global es contundente a propósito. Si algún componente necesita animación
  esencial, se re-habilita como el spinner.

#### I-08 · Racha de login · Hecho (23-11) · M
- **Referente**: PokerBros (bonos crecientes), Governor of Poker 3 (bonus periódico).
- **Aviso de diseño**: **no hay monedero**. Las fichas viven en la pila de cada mesa, no en el
  perfil. La recompensa debe ser **cosmética o de estatus** (tapete, dorso, insignia, título), o
  hay que crear antes una economía de fichas, que es otra decisión. Por eso esta ficha mide la
  racha y deja el premio para cuando exista el cosmético; no inventa fichas.
- **Qué se hizo**: `UserProfile` guarda `login_streak`, `best_login_streak` y `last_checkin`;
  `POST /api/users/me/checkin/` es idempotente por día, usa `timezone.localdate()` (no el reloj
  del móvil), suma si el último fue ayer y reinicia si hubo un hueco. La home llama al fichar y
  muestra “DÍAS SEGUIDOS” en la tarjeta de estado; los hitos 3/7/30/100 devuelven
  `milestone: true` para cuando haya algo que desbloquear.
- **Dónde**: `backend/apps/users/models.py`, migración `0003_...`, `users/views.py` (`checkin`),
  `apps/users/tests_checkin.py`, `front/src/app/core/services/user.service.ts` (`checkin()`),
  `features/home/home.ts` y `home.html`.
- **Hecho cuando**: dos llamadas el mismo día no suben la racha; un día saltado la reinicia y el
  mejor histórico no se pierde; hay tests de los cuatro casos y de la sesión anónima.
- **Riesgo**: zonas horarias. La racha es del servidor, no del dispositivo; queda documentado y
  probado con `localdate()`.

#### I-09 · Misión diaria opt-in · Siguiente · M
- **Referente**: PokerStars (misiones diarias con opt-in).
- **Qué**: una misión al día calculada sobre lo que ya se guarda: “gana 2 manos”, “juega 5 manos”,
  “gana una mano sin showdown”. El jugador la activa; al cumplirla, reclama un cosmético. Sin
  caducidad de 48 h ni cofres con temporizador.
- **Dónde**: `apps/poker/achievements.py` ya sabe leer `PokerHandRecord`/`PokerHandPlayer`; añadir
  `misiones.py` con el cálculo por fecha y un endpoint de reclamo; UI en `poker/history/` o home.
- **Hecho cuando**: el progreso coincide con las manos del día; reclamar dos veces no da dos
  premios; la misión se puede desactivar y no vuelve a aparecer ese día.
- **Riesgo**: consultas pesadas si se calcula en cada carga. Cachear por usuario/día o calcular
  solo al abrir la tarjeta.

#### I-10 · Rueda diaria de cosméticos · Explorar · M
- **Referente**: PokerStars (prize wheel), PokerBros (ruleta).
- **Qué**: una tirada al día con premios ya existentes (tapetes, dorsos, títulos). Sin monedero y
  sin compra.
- **Dónde**: front (`features/home/` o `features/poker/`), estado en `UserProfile`
  (`last_wheel_day`) y una tabla pequeña de cosméticos desbloqueados (`unlocked_themes` JSON).
- **Decisión previa**: ¿los cosméticos se desbloquean para siempre o solo se sortean? Sin esto,
  la rueda es un botón que no cambia nada.
- **Riesgo**: es la idea más cercana a un dark pattern. Si se hace, sin cuenta atrás ni
  “casi lo consigues”.

#### I-11 · Filtros y “ocultar mesas llenas” · Siguiente · S/M
- **Referente**: PokerStars, WPT Global (lobby 2025).
- **Qué**: en la lista de mesas vivas, filtros por ciegas, número de jugadores y estado; casilla
  “ocultar llenas”; favoritos guardados en `localStorage`. En móvil, los filtros van en una hoja
  inferior, no en una fila que se desborda.
- **Dónde**: `poker.html` (`.live`), `poker.ts`, `poker.service.loadLiveTables()`. Si falta el
  máximo de asientos, añadirlo a `LiveTable`/serializer del backend.
- **Hecho cuando**: con 20 mesas, el filtro deja solo las que cumplen; la elección se recuerda al
  volver; “ocultar llenas” usa plazas libres reales, no una estimación.
- **Riesgo**: que el refresco periódico rehaga la lista y cierre la hoja de filtros. Mantener el
  estado en signals, no en el DOM.

#### I-12 · Ficha de torneo completa · Siguiente · M
- **Referente**: WSOP.com.
- **Qué**: al abrir un torneo, estructura de ciegas, late registration, inscritos, premios y
  estado del bracket, sin salir de la ficha.
- **Dónde**: `features/game/tournament/` y `apps/tournament/serializers.py` (campos que falten).
- **Hecho cuando**: se puede decidir si inscribirse sin abrir tres pantallas; los datos coinciden
  con el bracket.
- **Riesgo**: duplicar la lógica de premios en front y back. El servidor manda.

#### I-13 · Estadísticas propias ampliadas · Siguiente · M
- **Referente**: ClubGG, PokerCraft.
- **Qué**: además de wins/losses/ELO, mostrar manos jugadas, winrate por juego, showdowns ganados y
  mejor racha. Nada de datos de otros jugadores en tiempo real.
- **Dónde**: `users/views.py::_build_stats` y `features/profile/`.
- **Hecho cuando**: los números cuadran con el historial y no añaden consultas N+1.
- **Riesgo**: privacidad. Solo el propio usuario ve el detalle; el resto ve lo público.

#### I-14 · Compartir una mano del historial · Siguiente · S
- **Referente**: Chess.com (compartir partida), Discord.
- **Qué**: reutilizar el canvas de `shareResult()` para una mano concreta del historial/replay:
  cartas, bote, ganador y calle. Un botón en `poker/history`.
- **Dónde**: `features/poker/history/history.ts`, `hand-replay.ts`; extraer el dibujo a
  `core/ui/share-card.ts` para no duplicarlo.
- **Hecho cuando**: desde el replay se genera una imagen con la mano y el bote correctos.
- **Riesgo**: las cartas privadas de rivales no deben salir si la mano no llegó a showdown.

---

### Tanda 3 — Social y juego privado

#### I-15 · Clubes privados de póker con código · Siguiente · L
- **Referente**: ClubGG (ID de 6 dígitos), PokerStars Home Games, `apps/salas/` (4 caracteres para
  cartas españolas).
- **Qué**: crear una mesa privada de póker con código, invitar por enlace, elegir ciegas y tamaño;
  sin matchmaking ni bot de reserva. La mesa vive mientras haya gente.
- **Dónde**: `apps/poker/tables.py` (registro de mesas), `views.py`/`urls.py` (crear/unirse por
  código), `consumers.py` (entrada por código), lobby `poker.html`. Reutilizar el alfabeto sin
  O/0/I/1 de `salas/rooms.py`.
- **Hecho cuando**: dos personas con el código juegan sin pasar por la cola; sin código no se
  puede entrar; la mesa se recoge al quedarse vacía.
- **Riesgo**: el registro de mesas es **por proceso**. Con varias réplicas hace falta Redis o
  sticky sessions; documentarlo antes de prometerlo.

#### I-16 · Fold & watch · Explorar · S
- **Referente**: 888poker (“fold, watch and play”).
- **Qué**: al retirarse, seguir viendo la mano hasta el final en vez de salir; desde ahí, un botón
  para volver a la cola.
- **Estado real**: el jugador retirado **ya sigue recibiendo el estado** de la mesa; lo que falta
  es que la UI lo diga y ofrezca “ver el final”. Verificar antes de programar.
- **Dónde**: `poker.html` (estado `folded` del asiento propio), `poker.ts`.
- **Hecho cuando**: tras retirarse se ve el board y el resultado, y se puede saltar a otra mesa.
- **Riesgo**: confundir “retirado” con “espectador”; el chat y los asientos deben seguir claros.

#### I-17 · Revancha con la misma gente · Explorar · M/L
- **Referente**: Chess.com (rematch).
- **Qué**: la revancha actual vuelve a la cola y puede emparejar con otro. La versión completa
  reutiliza la mesa y reinicia pilas, conservando asientos.
- **Dónde**: `PokerTable` (reset de stacks/mano), `consumers.py` (mensaje `rematch`), `poker.ts`.
- **Hecho cuando**: dos jugadores pulsean revancha y vuelven a la misma mesa con las pilas
  iniciales; si uno se va, el otro vuelve a la cola.
- **Riesgo**: estado autoritativo a medias. El servidor debe reiniciar, no el cliente.

#### I-18 · Fast-fold interno · Explorar · L
- **Referente**: 888 SNAP, GG Rush & Cash.
- **Qué**: al retirarse, el jugador entra al instante en otra mesa con una mano nueva. Requiere un
  pool de mesas compartido, no pares aislados.
- **Dónde**: `apps/poker/tables.py` y `queue.py`; probablemente un registro de pool con Redis.
- **Hecho cuando**: retirarse no te deja esperando; la mano nueva empieza en <1 s.
- **Riesgo**: es un cambio de arquitectura, no una pantalla. No empezar sin decidir el pool.

#### I-19 · Anti-colusión ligero · Explorar · M
- **Referente**: GGPoker WAD, WPT AceGuardian.
- **Qué**: informe (no castigo automático) de cuentas que comparten IP y tienen winrate anómalo,
  revisable por un humano. Sin guardar IPs más de lo necesario y con política de privacidad.
- **Dónde**: comando de gestión en `apps/poker/management/commands/` o informe en admin; modelos
  de auditoría si se decide persistir.
- **Hecho cuando**: un caso de prueba (dos cuentas, misma IP, mismo patrón) aparece en el informe.
- **Riesgo**: privacidad y falsos positivos. Es una ayuda a la revisión, no una sentencia.

#### I-20 · RNG documentado y registro sellado · Siguiente · S/M
- **Referente**: PokerStars (RNG auditado), WPT (FairGame).
- **Qué**: documentar en `docs/` qué RNG usa el barajado, dónde vive y cómo se prueba; añadir un
  test que verifique que no se usa `random` global sin semilla y que el reparto no se puede
  predecir desde el cliente.
- **Dónde**: `backend/apps/poker/` (motor de barajado), `docs/POKER_ONLINE.md`.
- **Hecho cuando**: cualquiera puede leer cómo se baraja y hay un test que lo respalda.
- **Riesgo**: si el motor usa `random` en vez de `secrets`, hay que cambiarlo antes de documentar
  lo que no es.

---

### Tanda 4 — La apuesta grande: entender la mano

#### I-21 · Revisión post-mano · Explorar · L
- **Referente**: Chess.com Game Review, WPT QuintAce.
- **Qué**: al terminar una mano, una tarjeta con: equity aproximada al igualar, decisión más cara
  (“igualaste 40 con 18 %”), y un botón “repetir la decisión”. Sin solucionador completo; con
  reglas claras y honestas sobre lo que se mide.
- **Dónde**: `apps/poker/` (evaluador y probabilidades), `poker/history/hand-replay` y
  `poker.ts`; reutilizar `poker_hand.py`/`hand_eval` para fuerza de mano.
- **Hecho cuando**: la cifra coincide con la cuota mostrada en mesa y el texto no promete precisión
  que no tiene.
- **Riesgo**: calcular equity real es caro. Empezar por “fuerza de tu mano vs. rango estimado” o
  por la cuenta de cuota, que ya está hecha.

#### I-22 · Modo asíncrono para brisca/tute/mus · Explorar · L
- **Referente**: Board Game Arena (24 h/jugada, reloj con recarga).
- **Qué**: partidas que viven entre sesiones: N jugadas al día, notificación y reloj con skip.
  Es un modelo distinto al WebSocket en vivo.
- **Dónde**: `apps/salas/` (hoy efímero), modelos de partida y turnos, notificaciones, front de
  `features/games/`.
- **Hecho cuando**: una partida sobrevive a cerrar el navegador y avisa cuando te toca.
- **Riesgo**: es el cambio más grande de la lista; no mezclarlo con la limpieza de mesas en vivo.

---

## 5. Plan por tandas

| Tanda | Contenido | Depende de | Estado |
|---|---|---|---|
| **1** | I-01…I-06 (quick seat, revancha, barra, emotes, tarjeta, copy) | — | **Hecha** |
| **2** | I-07 movimiento, I-08 racha, I-11 filtros, I-14 compartir mano | Tanda 1 | **Parcial**: I-07 e I-08 hechos; I-11 e I-14 siguientes |
| **3** | I-09 misión, I-12 ficha de torneo, I-13 stats, I-20 RNG | Tanda 2 | Siguiente |
| **4** | I-15 clubes privados, I-16 fold & watch, I-17 revancha real | Decidir registro de mesas | Explorar |
| **5** | I-18 fast-fold, I-21 revisión post-mano | Tanda 4 + motor | Explorar |
| **6** | I-19 anti-colusión, I-22 asíncrono | Producto | Explorar |

**Regla de oro**: cada ficha entra con tests, i18n en ES/EN/FR y una comprobación en móvil. Si una
idea no se puede verificar con un test o con una captura, todavía no está hecha.

---

## 6. Lo que NO hay que copiar

- **Todo lo que depende de dinero real**: rakeback, staking, seguros de bad beat, cashier, bonos
  por depósito. Sin depósito no significan nada y añaden fraude.
- **KYC, geolocalización y regulación multi-estado** (WSOP.com): complejidad enorme para fichas
  virtuales.
- **Dark patterns**: cofres que caducan, FOMO con temporizador, compra de fichas, “casi lo
  consigues”. La retención debe venir de jugar con amigos y de mejorar.
- **HUDs de terceros**: en GGPoker están prohibidos; su sustituto es un HUD propio. Aquí, solo
  estadísticas propias y nada que dé ventaja en tiempo real.
- **SnapCam/streaming WebRTC en mesa**: coste alto y poco valor entre amigos.
- **Multi-mesa ×4 en escritorio**: sin fast-fold, multiplica la complejidad de UI y de estado; no
  es un quick win.

---

## 7. Fuentes

Póker:

- PokerStars — Quick Seat, filtros y favoritos: <https://www.pokerstars.com/poker/room/features/software-news/> · <https://www.pokerstars.com/help/articles/client-feature-favorites/11023>
- PokerStars — misiones diarias: <https://www.pokerstars.com/poker/promotions/daily-missions> · rueda: <https://www.pokerstars.com/poker/promotions/daily-prize-wheel-2/>
- PokerStars — escuela: <https://www.pokerstars.fr/en/poker/school> · RNG: <https://www.pokerstars.com/rng> · juego responsable: <https://www.pokerstars.com/casino/about/responsible-gaming> · Home Games: <https://www.pokerstars.com/poker/home-games/>
- GGPoker — Smart Betting: <https://ggpoker.com/poker-games/smart-betting/> · features de mesa: <https://ggpoker.com/poker-card-games/table-features/> · seguridad: <https://ggpoker.com/blog/new-security-measures-at-ggpoker/>
- 888poker — SNAP: <https://888poker.com/poker-games/snap>
- WPT Global — lobby y mesa: <https://worldpokerdeals.com/blog/how-has-the-wpt-global-client-lobby-changed> · <https://worldpokerdeals.com/rakeback-deals/wpt-global-review>
- WSOP.com — lobby y multi-mesa: <https://usgamingreview.com/online-poker/wsop-review/>
- ClubGG — clubs y reglas: <https://www.clubgg.com/> · <https://help.clubgg.com/article/Clubs---Basics>
- PokerBros — clubs, racha y economía: <https://pokernews.com/news/2020/07/pokerbros-play-poker-the-way-you-want-when-you-want-37631.htm>

Juegos y UX:

- Board Game Arena — turnos asíncronos y reloj: <http://en.boardgamearena.com/doc/Turn_based_FAQ> · <http://en.boardgamearena.com/doc/Game_clock>
- Colonist.io — ranked, temporadas y placements: <https://colonist.instantdocsbase.com/doc/how-does-the-ranked-system-work> · <https://blog.colonist.io/colonist-io-2025-summary>
- Chess.com — Game Review y ligas: <https://support.chess.com/en/articles/8584089-how-does-game-review-work> · <https://www.chess.com/article/view/chesscom-features>
- Balatro — juice y ajustes de velocidad: <https://teemo.dev/game-design/balatro/systems/game-feel-and-juice> · <https://blakecrosley.com/guides/design/balatro>
- Marvel Snap — partidas cortas y “Escaped!”: <https://www.theguardian.com/games/2022/nov/11/i-craved-a-bite-size-experience-ben-brode-on-the-making-of-marvel-snap> · <https://www.theverge.com/23437497/marvel-snap-developer-design-interview-mobile-steam>
- Duolingo — jugar antes de registrarse: <https://screensdesign.com/articles/duolingo-onboarding-design> · <https://www.925studios.co/blog/duolingo-design-breakdown>
- Discord — comunidad y bots: <https://docs.discord.com/developers/game-development/how-to-keep-your-players-engaged>
