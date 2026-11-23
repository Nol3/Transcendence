# Auditoría y plan de modernización del frontend

Fecha: 23-11-2026 · Alcance: `front/` completo (Angular 20) · Estado: auditoría hecha, Fase 0 aplicada.

Este documento no es una lista de desiderátums: cada hallazgo tiene una medición o un archivo detrás,
y cada tarea del plan tiene un criterio de aceptación. Lo que ya está hecho va marcado como **Hecho**;
lo demás es **Siguiente** (diseñado, sin código) o **Explorar** (depende de una decisión de producto).

---

## 1. Resumen ejecutivo

El frontend tiene una identidad visual coherente (arcade neón, pixel font, cartas 8-bit) y una base
técnica mejor de lo que suele verse en un proyecto de 42: Angular standalone con lazy loading, i18n
en ES/EN/FR, 184 tests unitarios, suite e2e, axe en CI y un design system con tokens. El problema no
es la falta de estilo: es que **el estilo no está sistematizado en las pantallas de juego**.

La auditoría encontró tres defectos reales que el usuario ya veía:

1. **Contenido pegado al borde izquierdo** en `/brisca`, `/tute`, `/mus` y `/mentiroso`: el atajo
   `padding: … 0 …` de cada página anulaba el `padding-inline` de `.container`. El bloque de inicio
   además tenía `max-width: 44rem` sin `margin-inline: auto`. Medido: `x=0`; ahora `x=272` en 1280 px.
2. **Desbordamiento horizontal de 112 px en `/tournament` a 390 px**: el grid pedía 340 px fijos y
   las tres pestañas no cabían. Ahora `overflow: 0` y pestañas cortas en móvil.
3. **Objetivos táctiles y textos demasiado pequeños**: enlaces del header de 29 px de alto, botones
   de 36 px, iconos de 26 px y navegación a 8 px. Se han subido los botones y el header; quedan los
   iconos del póker y parte de la tipografía para la Fase 1.

Lo que sigue no es “rediseñar por rediseñar”. La dirección propuesta es **arcade legible**: conservar
la identidad, pero con jerarquía, espaciado y legibilidad de producto moderno. El plan completo tiene
8 fases y 46 tareas; la Fase 0 ya está aplicada y verificada.

---

## 2. Cómo se ha medido

| Qué | Cómo |
|---|---|
| Rutas | 11 pantallas autenticadas: `/`, `/games`, `/brisca`, `/tute`, `/mus`, `/mentiroso`, `/culo`, `/poker`, `/tournament`, `/profile`, `/chat` |
| Tamaños | 1280×800 (escritorio) y 390×800 (móvil) |
| Herramienta | Playwright Chromium con la API simulada de `e2e/helpers.ts` (login real contra mocks) |
| Métricas | `scrollWidth - innerWidth`, `getBoundingClientRect()` de bloques y controles, `font-size` computado, elementos con `x < 10`, imágenes sin `alt`, número de `h1/h2` |
| Accesibilidad | `e2e/a11y.spec.ts` con axe-core (12 pantallas, solo falla por `critical`/`serious`) |
| Rendimiento | `ng build --configuration production`; tamaños de bundle del informe de Angular |
| Código | Lectura de plantillas, SCSS, rutas, servicios y componentes compartidos |

Las capturas de la auditoría se generaron con Playwright y no se versionan: son evidencia de esta
pasada, no un artefacto del producto. Los comandos de 13.2 permiten reproducirlas.

---

## 3. Inventario de pantallas

| Ruta | Título real | `h1` | Estado visual | Problema principal |
|---|---|---|---|---|
| `/` | Home | Sí | Hero + stats + leaderboard + side panel | CTAs compitiendo; hero muy alto; toast tapa stats |
| `/games` | Games | No (`h2`) | Parrilla de tarjetas | Falta `h1`; tarjetas muy uniformes |
| `/brisca` | Brisca | No (`h2`) | Menú centrado (Hecho) | Falta `h1`; reglas en modal propio |
| `/tute` | Tute | No (`h2`) | Menú centrado (Hecho) | SCSS heredado de brisca vía `@use` |
| `/mus` | Mus | No (`h2`) | Menú centrado (Hecho) | SCSS heredado de brisca vía `@use` |
| `/mentiroso` | Cheat | No (`h2`) | Menú centrado (Hecho) | Duplica el bloque `.inicio` |
| `/culo` | Culo | No (`h2`) | Menú centrado (Hecho) | Duplica el bloque `.inicio` |
| `/poker` | Poker | No (`h2`) | Lobby denso | Iconos de 26 px; mucha información sin jerarquía |
| `/tournament` | Tournament | Sí | Pestañas + lista | Desbordamiento móvil (Hecho); falta estado vacío con acción |
| `/profile` | Profile | No (`h2`) | Cuatro tarjetas | `Edit Profile` de 28 px; secciones sin navegación |
| `/chat` | Chat | No (`h2`) | Dos columnas | Estado vacío pobre; móvil apretado |

Rutas no auditadas visualmente en esta pasada: `/login`, `/register`, `/forgot-password`,
`/reset-password`, `/privacy`, `/terms`. Entran en la Fase 4 y en la checklist de la Fase 8.

---

## 4. Hallazgos

Severidad: **S1** rompe la pantalla, **S2** afecta a la tarea principal o a accesibilidad, **S3**
degrada la experiencia o la mantenibilidad, **S4** deuda menor.

| ID | Sev. | Hallazgo | Evidencia | Estado |
|---|---|---|---|---|
| F-01 | S1 | El contenido de los juegos se pega al borde izquierdo | `.brisca`/`.mentiroso` usan `padding: … 0 …` y anulan `.container`; `.inicio` mide `x=0` | **Hecho** |
| F-02 | S1 | El bloque de explicación no está centrado | `max-width: 44rem` sin `margin-inline: auto`; queda a la izquierda | **Hecho** |
| F-03 | S2 | `/tournament` desborda 112 px a 390 px | Grid `minmax(340px,1fr)` + tres pestañas largas en una fila | **Hecho** |
| F-04 | S2 | Objetivos táctiles por debajo de 44 px | Header 29 px; botones 36 px; iconos del póker 26 px; `Edit Profile` 28 px | **Parcial** |
| F-05 | S2 | Tipografía de interfaz a 8–10 px | Nav 8 px; labels de botón 8 px; stats 8 px | **Parcial** |
| F-06 | S2 | Falta `h1` en 9 de 11 pantallas | Solo `/` y `/tournament` tienen `h1`; los juegos usan `h2` como título | **Siguiente** |
| F-07 | S2 | El enlace “View Full Rankings” mide 8 px de alto | `a` sin `display`, `padding` ni `min-height` | **Hecho** |
| F-08 | S3 | Jerarquía de CTAs confusa en la home | “Poker” sólido compite con “Play Now” outline y con el CTA del panel derecho | **Siguiente** |
| F-09 | S3 | Cada juego duplica cabecera, botón de sonido y volver | `brisca__cabecera`, `mentiroso__cabecera`, `culo__cabecera`… | **Siguiente** |
| F-10 | S3 | Los diálogos de reglas son artesanales y distintos | `.reglas` en brisca/mentiroso/culo; tute/mus lo heredan de brisca por `@use` | **Siguiente** |
| F-11 | S3 | Los diálogos no cierran con Escape ni con clic fuera | `FocoDialogoDirective` atrapa el foco, pero no hay `keydown.escape` ni backdrop | **Siguiente** |
| F-12 | S3 | Falta un sistema de estados | Loading/empty/error se resuelven distinto en cada pantalla | **Siguiente** |
| F-13 | S3 | El toast se solapa con la barra de stats en la home | Captura 1280: toast sobre la zona de estadísticas | **Siguiente** |
| F-14 | S3 | `BRACKET` y `Back` estaban sin traducir | `[title]="'BRACKET'"`, texto `Back` en el detalle de torneo | **Hecho** |
| F-15 | S4 | Colores y píxeles crudos fuera de tokens | 20 usos de `#4ad9d9`, 13 de `#29e0ff`, 10 de `#14141f`; 465 valores `px` | **Siguiente** |
| F-16 | S4 | Avisos de Sass por `mixed-decls` | Build de producción con varios `Deprecation [plugin angular-sass]` | **Siguiente** |
| F-17 | S4 | Sin regresión visual automatizada | No hay snapshots de pantallas; los bugs de layout se ven a ojo | **Siguiente** |
| F-18 | S4 | `footer` y `chat` se aprietan en móvil | Tres columnas de enlaces y dos paneles sin colapsar | **Siguiente** |

---

## 5. Lo que se ha arreglado en esta pasada (Fase 0)

### 5.1 Centrado y gutters de las páginas de juego

**Antes:** `.brisca` declaraba `padding: 1rem 0 2rem`. Ese atajo pone `padding-left/right: 0` y, como
el SCSS del componente se carga después de `styles.scss`, ganaba a `.container` (que sí tenía
`padding-inline: 24px`). Resultado: título, intro y botones en `x=0`.

**Después:** `padding-block` conserva el padding lateral del contenedor. `.inicio` pasa a ser una
ficha centrada de `min(100%, 46rem)`, con borde, superficie y sombra suaves, intro a 38rem, botones
centrados y ajustes alineados a la izquierda dentro de la ficha.

**Medición (1280 px):**

| Métrica | Antes | Después |
|---|---|---|
| `x` de `.inicio` | 0 | 272 |
| Ancho de `.inicio` | 704 | 736 |
| `x` del `h2` | 0 | 24 |
| Elementos de texto con `x < 10` | 3 | 0 |

Aplica a `/brisca`, `/tute`, `/mus` (los tres comparten `brisca.scss`) y a `/mentiroso`. `/culo`
recibe el mismo tratamiento visual y queda centrado con `max-width: 34rem`.

**Archivos:** `features/games/brisca/brisca.scss`, `features/games/mentiroso/mentiroso.scss`,
`features/games/culo/culo.scss`.

### 5.2 Torneo en móvil

**Antes:** a 390 px, `scrollWidth - innerWidth = 112`. El grid pedía `minmax(340px, 1fr)` dentro de
un contenedor de 326 px y las pestañas no cabían; el header tampoco envolvía.

**Después:**

- `padding: clamp(1rem, 4vw, 2rem)` en la página.
- `flex-wrap` y `gap` en el header.
- Pestañas con `overflow-x: auto` y etiquetas cortas (`Activos`, `Próximos`, `Finalizados`) por
  debajo de 560 px.
- Grid con `minmax(min(100%, 340px), 1fr)`.

**Medición:** `overflow` 112 → 0 en 390 px; sigue en 0 en 1280 px.

**Archivos:** `features/game/tournament/tournament.{html,scss}`, `front/public/i18n/{es,en,fr}.json`.

### 5.3 Objetivos táctiles y enlace de rankings

- Header: enlaces y botones a 11 px de fuente y `min-height: 40px` (antes 29 px).
- `app-button`: `min-height` 36/42/48 px y 44 px en puntero grueso (antes 33–36 px).
- “View Full Rankings”: de 8 px de alto a 40 px con padding.
- `BRACKET` y `Back` pasan por i18n.

Quedan pendientes los iconos de 26 px del póker, los selects de 30 px y `Edit Profile` de 28 px;
están en la Fase 1 y en la Fase 4.

### 5.4 Verificación

| Comprobación | Resultado |
|---|---|
| `ng build --configuration production` | OK; initial total 373.59 kB (105.52 kB transfer) |
| `ng test --watch=false` | 13 ficheros, **184 tests OK** |
| `npm run lint` | Sin errores |
| `npx playwright test ... a11y.spec.ts` | **12/12 OK** (sin `critical`/`serious`) |
| Auditoría de layout propia | `overflow: 0` y `pegados: []` en las 11 rutas a 390 y 1280 |
| Medición de `.inicio` | `x=272`, ancho 736, en brisca/tute/mus/mentiroso |

La suite móvil encontró un efecto colateral real: el nuevo `min-height: 44px` de `app-button`
pisaba los 56 px de los controles de mesa del Culo (la encapsulación de Angular daba más
especificidad al componente). Se corrigió con `.controles__botones button.btn` y el test volvió a
verde. Es la prueba de que el plan necesita la Fase 8 (red de seguridad visual), no solo revisar
capturas a ojo.

### 5.5 Segunda pasada: sistema de juego y títulos

Después de la auditoría se encontró un fallo mayor que ninguna captura previa había detectado:
**todos los `app-pixel-title` se pintaban vacíos**. El componente tenía un `<ng-content>` dentro de
cada `@case` de un `@switch`; Angular solo conserva una proyección, así que “Login”, “Games”,
“Player Profile” u “Online Poker” no aparecían. Se sustituyó por una única proyección con
`ngTemplateOutlet` y se añadió `pixel-title.spec.ts` para que no vuelva.

En la misma pasada:

- **GameShell y RulesDialog compartidos** para Brisca, Tute, Mus, Mentiroso y Culo: una sola
  cabecera con `h1`, un solo diálogo con Escape, clic en el fondo, bloqueo de scroll y foco.
- **Binding roto** `[style.--i]="$index"` que se pintaba como texto en las mesas de Brisca, Tute y
  Mentiroso; ahora es un atributo del `<li>`.
- **Selects que ignoraban su valor inicial** en los menús (Culo mostraba 3 jugadores y una baraja
  vacía en vez de 4 y 1): `[selected]` en cada opción.
- **Mesa centrada** (`margin-inline: auto`) y overlays de final con `padding` y `width: min(32rem,
  100%)`.
- **Torneo**: modal de creación con `role="dialog"`, `aria-modal`, foco atrapado, Escape, labels
  asociados y error visible del nombre.
- **Juegos**: grid sin overflow a 320 px, iconos en un marco homogéneo de 44 px y títulos con altura
  mínima para alinear las tarjetas.
- **Home**: CTA de invitado con texto de acción, “TOURNAMENTS” en plural, `WINS`/`UNKNOWN`/estado
  online traducidos.
- **Chat**: un solo estado vacío en móvil y CTA secundaria.
- **Footer**: enlaces de cuenta según sesión, “Games” en vez de “Play” y redes con target de 44 px.
- **Accesibilidad**: `aria-live` en turno y registro, emojis decorativos con `aria-hidden`,
  `prefers-reduced-motion` global, cierre de modal a 44 px y errores de auth con `role="alert"`.
- **i18n**: `game.tute.how`, `game.mus.how`, `tournament.nameError`, `common.online/offline/unknown`
  y textos de registro/recuperación.

**Verificación de la segunda pasada:** build OK, **185 unitarios**, lint limpio, **65 e2e de
Chromium + 7 skipped**, **4 e2e móviles** y auditoría propia de 64 combinaciones ruta × ancho con
`overflow: 0` y un `h1` por pantalla.

---

## 6. Diagnóstico por área

### 6.1 Layout y page shell

**Bien:** existe `.container` con `max-width: 1280px`, `margin-inline: auto` y padding lateral; hay
tokens de spacing y de radios.

**Falla:** el shell no protege a `.container` de que un componente lo pise. Cada página decide su
padding, su ancho y su alineación. No hay un `PageShell` que garantice gutters, ritmo vertical y
ancho de lectura. La home ocupa 1280 px para un leaderboard y tres tarjetas; en móvil el footer y el
chat se aprietan.

**Decisión:** un `PageShell` (ancho, gutters, `min-height`) y un `PageHeader` (título, subtítulo,
acciones) compartidos. Las páginas dejan de declarar padding propio; como mucho, `padding-block`.

### 6.2 Jerarquía y tipografía

**Bien:** la fuente pixel da identidad y los títulos neón se reconocen. Los tokens de color de texto
ya se corrigieron para AA (`--color-text-muted: #8888aa`).

**Falla:** el pixel font se usa para navegación, botones, etiquetas y stats a 8–10 px. Eso no es
“retro”, es ilegible. La jerarquía se apoya en el color neón, no en tamaño/peso. Faltan `h1` y los
niveles de heading no siempre siguen el contenido.

**Decisión:** tres roles tipográficos:

- **Display** (pixel): solo `h1`, cifras grandes y logo. Nunca párrafos.
- **UI** (Inter): navegación, botones, labels, formularios. Mínimo 12 px; ideal 13–14 px.
- **Lectura** (Inter): párrafos a 14–16 px, `line-height` 1.6–1.75, ancho 60–72 caracteres.

### 6.3 Navegación e información

**Bien:** header sticky, enlace activo, menú móvil, cinco destinos claros, `games` centraliza el
catálogo.

**Falla:** no hay breadcrumb ni contexto de juego en el header; “Back to games” es un enlace de
23 px. El hub no recuerda el último juego ni permite filtrar. La home y `/games` compiten por ser
la entrada. No hay “continuar partida” ni “última mesa”.

**Decisión:** header con `Games` como entrada principal y breadcrumb en juegos; hub con “Seguir
jugando” y filtros por modo/número de jugadores; un solo CTA primario por pantalla.

### 6.4 Experiencia de juego y diálogos

**Bien:** los cinco juegos comparten lenguaje visual de mesa; el foco de los diálogos está atrapado
y se devuelve al cerrar; hay sonido y ajustes por juego.

**Falla:** cada juego replica cabecera, sonido, volver y reglas. Tute y Mus heredan el SCSS de Brisca
con `@use`, lo que crea una dependencia invisible: un cambio en Brisca puede romper Tute. Los
diálogos no cierran con Escape ni con clic en el fondo. Las reglas son párrafos sueltos, sin
secciones ni ejemplos visuales.

**Decisión:** `GameShell` (cabecera + acciones + slot), `GameMenu` (intro + modos + ajustes),
`RulesDialog` (secciones, cierre con Escape/backdrop, foco) y `ConfirmDialog`. Migrar los cinco
juegos en dos tandas, empezando por Brisca y Mentiroso.

### 6.5 Accesibilidad

**Bien:** axe pasa 12/12 en `critical/serious`; hay foco atrapado en diálogos; `prefers-reduced-motion`
y ajuste manual; foco visible en botones.

**Falla:** textos de 8 px, targets de 26–36 px, falta `h1`, diálogos sin Escape, iconos sin etiqueta
visible en el póker y estados que dependen solo del color (verde/rojo). El contraste de algunos
textos secundarios y del pie sigue justo.

**Decisión:** AA como suelo, no como extra. Checklist por PR: teclado, 200 % zoom, 320 px, axe,
targets 44 px, `h1` único, texto alternativo y `aria-live` para cambios de estado.

### 6.6 Responsive

**Bien:** no hay overflow en 10 de 11 rutas; el header colapsa a hamburguesa; las cartas se adaptan.

**Falla:** el torneo desbordaba; el footer mantiene tres columnas; el chat tiene dos paneles fijos;
el póker tiene controles de 26 px. Los breakpoints se improvisan por componente.

**Decisión:** breakpoints documentados (`320`, `560`, `768`, `1024`, `1440`) y un mixin
`responder(desde)`; probar 320 px como mínimo real, no 390.

### 6.7 Estados y feedback

**Bien:** hay spinner, toasts y algunos `empty-state`.

**Falla:** no hay esqueleto de carga en la mayoría de listas; los errores se muestran como texto
suelto; no hay estado “sin conexión” ni “reconectando” en WebSocket; el toast se coloca encima del
contenido; no hay confirmación al salir de una mesa en curso.

**Decisión:** un `StateView` con cuatro variantes (`loading`, `empty`, `error`, `offline`), skeletons
en listas, `aria-live` para cambios y confirmación de salida en partidas activas.

### 6.8 Rendimiento

**Bien:** lazy loading por ruta; initial total 373.59 kB (105.52 kB transfer); los juegos pesan
26–57 kB cada uno; PWA y presupuesto Lighthouse ya existen.

**Falla:** `index.data` del WASM pesa 14 MB y no se puede reconstruir en esta máquina; las fuentes
pixel se cargan enteras; no hay presupuesto de bundle en CI; los avisos de Sass indican deuda.

**Decisión:** presupuesto por ruta en `angular.json`/Lighthouse CI, `font-display: swap`, subset de
fuentes, y medir LCP/INP/CLS en las tres pantallas principales. El WASM se trata aparte.

### 6.9 i18n y contenido

**Bien:** tres idiomas completos, claves por juego, `TranslatePipe` en casi toda la UI.

**Falla:** `WINS` en la home, `VS` en el bracket y dos textos del torneo estaban fuera de i18n;
no hay plurales ni formato de fechas/números por locale; cambiar idioma recarga la app.

**Decisión:** lint de claves, plurales ICU, `Intl` para fechas y números, cambio de idioma sin
recarga y un pseudo-locale para detectar textos que se salen.

### 6.10 Arquitectura y mantenibilidad

**Bien:** standalone components, lazy routes, servicios con signals, catálogo único de juegos,
tests de motores separados de la UI.

**Falla:** componentes de 360–469 líneas y plantillas de hasta 435 líneas; cabeceras de juego
duplicadas; SCSS compartido por `@use` en lugar de un componente; 465 `px` crudos; estilos globales
y de componente compiten (el bug F-01 es exactamente eso).

**Decisión:** extraer `GameShell`, `GameHeader`, `GameMenu`, `RulesDialog`; mover estilos de layout a
utilidades globales; prohibir `padding` atajo en raíces con `.container`; Stylelint para tokens.

### 6.11 Testing y gobernanza

**Bien:** 184 unitarios, e2e de flujos reales, axe, presupuesto Lighthouse.

**Falla:** no hay regresión visual; los tests e2e no miden layout; no hay checklist de PR visual;
los bugs de padding no los detecta ningún test.

**Decisión:** Playwright con snapshots de las 11 rutas a 390/1280, un test de “sin overflow” y otro
de targets mínimos; checklist de PR y revisión de diseño en cada fase.

---

## 7. Dirección de diseño: “arcade legible”

### 7.1 Contrato de diseño

| Pregunta | Respuesta |
|---|---|
| ¿Qué trabajo hace la pantalla? | Meter al jugador en una partida en menos de tres clics, sin leer un manual. |
| ¿Acción primaria? | Una sola por pantalla: Jugar / Entrar / Crear / Guardar. |
| ¿Qué se conserva? | Fondo oscuro, neón como acento, pixel font en display, cartas 8-bit, sonido. |
| ¿Qué se cambia? | Tipografía de UI a Inter 12–14 px, targets 44 px, superficies en capas, jerarquía por tamaño. |
| ¿Qué se rechaza? | SaaS genérico, gradientes por todas partes, todo redondeado, párrafos en pixel font, modales dentro de contenedores con `transform`. |
| ¿Cómo se mide? | 0 overflow a 320 px, 0 `critical` en axe, 100 % targets ≥44 px en táctil, LCP <2.5 s. |

### 7.2 Tokens que faltan

```scss
// Superficies semánticas (hoy cada componente inventa rgba)
--surface-1: #0c0c14;
--surface-2: #12121e;
--surface-3: #1a1a2c;
--surface-4: #1e1e30;

// Texto
--text-display: #f4f4ff;
--text-body: #d8d8ea;
--text-muted: #9a9abc;   // revisar contraste sobre surface-2

// Tipografía de UI
--font-ui: 0.8125rem;    // 13px
--font-ui-sm: 0.75rem;   // 12px
--leading-ui: 1.45;

// Foco y targets
--focus-ring: 0 0 0 3px #05050a, 0 0 0 6px var(--color-neon-magenta);
--target-min: 44px;
```

### 7.3 Reglas de composición

1. Un `h1` por pantalla; el pixel font solo en `h1`, cifras y logo.
2. Párrafos a 14–16 px, máximo 72 caracteres por línea.
3. Una tarjeta no se usa para todo: las listas densas van en filas, no en cards.
4. El neón marca estado/acción, no decora secciones enteras.
5. Los botones primarios son sólidos; los secundarios, outline; los terciarios, texto.
6. Nada de `padding` atajo en raíces que también usen `.container`: `padding-block`.
7. Los modales se montan en el `body` o en un `CDK Overlay`, nunca dentro de un ancestro con
   `transform`/`filter`/`contain`.
8. En móvil, una columna; las tablas y tabs se desplazan dentro de su caja, no arrastran la página.
9. Movimiento 120–240 ms; con `reduce-motion`, 0.
10. Todo estado tiene texto, no solo color.

---

## 8. Plan por fases

Esfuerzo: **S** ≤ 1 tanda, **M** 1–2 tandas, **L** > 2 tandas o toca backend.

### Fase 0 · Correcciones que el usuario ya veía · Hecha

| ID | Tarea | Archivos | Aceptación | Esf. |
|---|---|---|---|---|
| FIX-01 | Gutters de juegos con `padding-block` | `brisca.scss`, `mentiroso.scss` | `h2` en `x=24` a 1280 | S |
| FIX-02 | Ficha de inicio centrada y responsive | `brisca.scss`, `mentiroso.scss`, `culo.scss` | `.inicio` centrado a 390/1280 | S |
| FIX-03 | Torneo sin overflow móvil | `tournament.{html,scss}`, i18n | `overflow=0` a 390 | S |
| FIX-04 | Targets de header/botones y enlace de rankings | `header.scss`, `button.scss`, `home.scss` | ≥40 px; 44 px en táctil | S |
| FIX-05 | `BRACKET`/`Back` por i18n | `tournament.html` | Sin texto inglés fijo | S |

### Fase 1 · Fundamentos del design system · Siguiente

Objetivo: que el sistema impida los bugs en vez de arreglarlos uno a uno.

| ID | Tarea | Archivos | Aceptación | Esf. |
|---|---|---|---|---|
| DS-01 | Tokens de superficie, texto y tipografía UI | `styles.scss` | Tokens documentados y usados en 3 pantallas piloto | M |
| DS-02 | Escala tipográfica con roles display/UI/lectura | `styles.scss`, `docs/DESIGN_SYSTEM.md` | Ningún texto de UI <12 px | M |
| DS-03 | Utilidades `.page-shell`, `.page-header`, `.stack`, `.cluster` | `styles.scss` | Home, Games y Profile las usan | M |
| DS-04 | Foco único y target mínimo | `styles.scss`, `button.scss` | `:focus-visible` consistente; 44 px táctil | S |
| DS-05 | Stylelint: prohibir hex crudos y `padding` atajo en raíces `.container` | `.stylelintrc`, CI | El bug F-01 no puede volver | M |
| DS-06 | Documento `docs/DESIGN_SYSTEM.md` con ejemplos y reglas | docs | Un nuevo componente sabe qué usar | S |

### Fase 2 · Shell y navegación · Siguiente

Objetivo: una sola estructura de página y una navegación que oriente.

| ID | Tarea | Archivos | Aceptación | Esf. |
|---|---|---|---|---|
| NAV-01 | `PageShell` y `PageHeader` compartidos | `shared/layout/` | Las 11 rutas los usan | M |
| NAV-02 | Header: nav 12 px, activo, menú móvil y `aria-current` | `header.*` | Teclado y 320 px OK | M |
| NAV-03 | Breadcrumb en juegos y torneo | `shared/navigation/` | “Games / Brisca” visible y navegable | S |
| NAV-04 | Skip link y `main` con `id` | `app.html`, `styles.scss` | Primer Tab lleva al contenido | S |
| NAV-05 | Footer responsive de 3 columnas a acordeón | `footer.*` | Sin overflow a 320 px | M |
| NAV-06 | Hub: “Seguir jugando”, filtros por modo y búsqueda | `games-hub.*` | Última partida a un clic | M |

### Fase 3 · Shell de juego y diálogos · Siguiente

Objetivo: quitar la duplicación de los cinco juegos y hacer las reglas legibles.

| ID | Tarea | Archivos | Aceptación | Esf. |
|---|---|---|---|---|
| GAME-01 | `GameShell` (cabecera, sonido, volver, slot) | `shared/game/` | Brisca y Mentiroso migrados | M |
| GAME-02 | `GameMenu` (intro, modos, ajustes, CTA) | `shared/game/` | Los cinco menús usan el mismo componente | M |
| GAME-03 | `RulesDialog` con secciones, Escape y backdrop | `shared/game/` | Cierra con Escape, clic y botón; foco OK | M |
| GAME-04 | Migrar Tute, Mus y Culo; retirar `@use '../brisca/brisca.scss'` | `tute.scss`, `mus.scss` | Sin dependencia cruzada | M |
| GAME-05 | Reglas con ejemplos visuales y “primera vez” | `shared/game/`, i18n | Se entiende sin leer 6 párrafos | L |
| GAME-06 | Confirmación de salida en partida activa | `shared/game/` | Salir pide confirmación | S |

### Fase 4 · Accesibilidad AA · Siguiente

Objetivo: que la app se pueda usar con teclado, lector y poca vista.

| ID | Tarea | Archivos | Aceptación | Esf. |
|---|---|---|---|---|
| A11Y-01 | Un `h1` por pantalla y orden de headings | 11 plantillas | axe sin `heading-order` | S |
| A11Y-02 | Targets ≥44 px en táctil (póker, selects, perfil) | `poker.scss`, `profile.scss` | 0 controles <44 px a 390 | M |
| A11Y-03 | Contraste de texto secundario y footer | `styles.scss` | AA en las 12 pantallas | M |
| A11Y-04 | Diálogos: Escape, backdrop, `aria-labelledby` | `shared/game/` | Probado con teclado | S |
| A11Y-05 | Estados con texto además de color | juegos, torneo | Daltónico puede jugar | M |
| A11Y-06 | 200 % zoom y 320 px sin pérdida | CSS | Sin scroll horizontal | M |
| A11Y-07 | axe en CI y checklist manual por PR | CI, docs | Falla el PR si hay `serious` | S |

### Fase 5 · Estados y feedback · Siguiente

| ID | Tarea | Archivos | Aceptación | Esf. |
|---|---|---|---|---|
| STATE-01 | `StateView` (loading/empty/error/offline) | `shared/ui/` | Las listas lo usan | M |
| STATE-02 | Skeletons en home, torneo, historial y chat | features | Sin salto de layout | M |
| STATE-03 | WebSocket: reconectando y sin conexión | `poker.service`, `salas` | El usuario sabe qué pasa | M |
| STATE-04 | Toast fuera del flujo de stats | `toast.scss` | No tapa contenido a 390 | S |
| STATE-05 | Confirmaciones destructivas unificadas | `shared/ui/` | Salir/borrar piden confirmación | S |

### Fase 6 · Rendimiento y PWA · Siguiente

| ID | Tarea | Archivos | Aceptación | Esf. |
|---|---|---|---|---|
| PERF-01 | Presupuesto de bundle por ruta | `angular.json`, CI | Falla si crece >10 % | S |
| PERF-02 | Fuentes: `swap`, subset y precarga | `index.html`, `styles.scss` | Sin FOIT; LCP estable | M |
| PERF-03 | Lighthouse CI en home, games y póker | CI | LCP <2.5 s, CLS <0.1 | M |
| PERF-04 | Medir INP en mesa y chat | Playwright/DevTools | <200 ms en 4G simulada | M |
| PERF-05 | Actualización de service worker visible | `app.ts`, PWA | Aviso “nueva versión” | S |

### Fase 7 · i18n y contenido · Siguiente

| ID | Tarea | Archivos | Aceptación | Esf. |
|---|---|---|---|---|
| I18N-01 | Cero textos fijos; lint de claves | plantillas, script | `WINS`, `VS` fuera | S |
| I18N-02 | Plurales ICU y formato de fecha/número | `i18n.service` | “1 mano / 2 manos” correcto | M |
| I18N-03 | Cambio de idioma sin recarga | `language-switcher` | Sin perder estado de mesa | M |
| I18N-04 | Pseudo-locale para detectar desbordes | i18n | QA ve textos largos | S |
| I18N-05 | Tono de marca y microcopy de reglas | i18n | Reglas en 2 niveles: resumen y detalle | M |

### Fase 8 · Calidad y gobernanza · Siguiente

| ID | Tarea | Archivos | Aceptación | Esf. |
|---|---|---|---|---|
| QA-01 | Snapshot visual de 11 rutas × 2 anchos | e2e | Un cambio de layout falla el PR | M |
| QA-02 | Test “sin overflow” y “targets ≥44” | e2e | Red de seguridad permanente | S |
| QA-03 | Checklist de PR visual y de accesibilidad | `CONTRIBUTING.md` | Se revisa antes de merge | S |
| QA-04 | Revisión de diseño por fase | docs | Cada fase cierra con capturas antes/después | S |
| QA-05 | Panel de métricas (bundle, LCP, axe) | CI | Tendencia visible | M |

---

## 9. Plan pantalla por pantalla

### 9.1 Home

- **Problema:** el hero ocupa demasiado, hay tres CTAs competitivos y el toast tapa las stats.
- **Qué hacer:** un CTA primario (“Jugar ahora”), “Poker” y “Torneo” como secundarios; bajar la
  altura del hero; mover el toast a una esquina que no tape datos; convertir el leaderboard en
  filas más densas; añadir “Continuar” si hay partida reciente.
- **Aceptación:** a 390 px, el primer CTA se ve sin scroll; solo un botón sólido; toast no tapa
  stats; `h1` único.

### 9.2 Games hub

- **Problema:** tarjetas uniformes, sin filtros ni memoria de lo último jugado.
- **Qué hacer:** agrupar por “Para jugar ya” y “Próximamente”; filtros por modo y jugadores; buscar;
  “Seguir jugando”; etiquetas legibles a 12 px.
- **Aceptación:** encontrar un juego concreto en <5 s; el último juego a un clic.

### 9.3 Menús de juego (Brisca, Tute, Mus, Mentiroso, Culo)

- **Problema:** ya centrados, pero cada uno con su propia estructura y texto plano.
- **Qué hacer:** `GameMenu` compartido; resumen de reglas en 3 bullets + “Ver reglas completas”;
  chips de jugadores/baraja/duración; CTA primario “Jugar con bots”, secundario “Online”; primera
  vez, reglas abiertas automáticamente una sola vez.
- **Aceptación:** los cinco menús comparten componente; misma jerarquía; reglas a un clic.

### 9.4 Mesa de juego

- **Problema:** cada juego replica cabecera y acciones; el estado “sin conexión” no se explica.
- **Qué hacer:** `GameShell`; indicador de turno y de conexión; confirmación al salir; manos
  responsive; atajos de teclado documentados; sonido con toggle persistente.
- **Aceptación:** jugar una mano completa solo con teclado; salir avisa; reconexión visible.

### 9.5 Póker

- **Problema:** lobby denso, iconos de 26 px, mucha información sin jerarquía.
- **Qué hacer:** agrupar en “Mesa rápida”, “Salas” y “Torneos”; targets 44 px; presets ya hechos;
  explicar ciegas y bote con etiquetas; historial más accesible.
- **Aceptación:** crear/entrar en mesa en ≤3 toques; 0 controles <44 px.

### 9.6 Torneo

- **Problema:** overflow corregido; el estado vacío no ofrece acción; el detalle mezcla bracket y
  metadatos.
- **Qué hacer:** estado vacío con “Crear torneo”; ficha con estructura, late reg y premios; tabs
  cortas (hecho); breadcrumb; `h1` correcto.
- **Aceptación:** en móvil no hay scroll horizontal; se decide si inscribirse en una pantalla.

### 9.7 Perfil

- **Problema:** cuatro tarjetas sin navegación; `Edit Profile` de 28 px; la accesibilidad está
  escondida al final.
- **Qué hacer:** sub-nav (Perfil / Estadísticas / Historial / Ajustes); targets 44 px; resumen de
  racha y logros; mover accesibilidad a Ajustes; estados de carga con skeleton.
- **Aceptación:** editar perfil y cambiar movimiento sin buscar; 0 targets pequeños.

### 9.8 Chat

- **Problema:** dos columnas fijas en móvil; estado vacío pobre.
- **Qué hacer:** una columna con lista→conversación en móvil; estado vacío con CTA; indicador de
  no leídos; `aria-live` para mensajes nuevos.
- **Aceptación:** usable a 320 px; se ve qué conversación tiene mensajes nuevos.

### 9.9 Auth y legal

- **Problema:** no auditadas visualmente; riesgo de targets y foco.
- **Qué hacer:** misma tarjeta y jerarquía; mostrar/ocultar contraseña con etiqueta; errores junto
  al campo; legal con índice y tipografía de lectura.
- **Aceptación:** formularios a 320 px, teclado y axe sin `serious`.

---

## 10. Backlog priorizado (impacto / esfuerzo)

| # | Tarea | Impacto | Esfuerzo | Fase |
|---|---|---|---|---|
| 1 | `GameShell` + `GameMenu` + `RulesDialog` | Alto | M | 3 |
| 2 | `PageShell` + `PageHeader` + `h1` | Alto | M | 2/4 |
| 3 | Tipografía UI 12–14 px y targets 44 px | Alto | M | 1/4 |
| 4 | Estados loading/empty/error/offline | Alto | M | 5 |
| 5 | Snapshot visual + test de overflow | Alto | M | 8 |
| 6 | Home: un CTA primario y hero más corto | Medio | S | 2 |
| 7 | Games hub con “Seguir jugando” y filtros | Medio | M | 2 |
| 8 | Torneo: estado vacío con acción y ficha completa | Medio | M | 2/5 |
| 9 | Perfil con sub-nav y accesibilidad en Ajustes | Medio | M | 2 |
| 10 | Chat responsive de una columna | Medio | M | 2 |
| 11 | Stylelint de tokens y padding | Medio | S | 1 |
| 12 | i18n: plurales, fechas y cambio sin recarga | Medio | M | 7 |
| 13 | Lighthouse CI y presupuesto de bundle | Medio | M | 6 |
| 14 | Reglas ilustradas y primera vez | Bajo | L | 3 |
| 15 | Pseudo-locale y microcopy | Bajo | S | 7 |

---

## 11. Métricas de éxito

| Métrica | Ahora | Objetivo |
|---|---|---|
| Overflow horizontal a 320/390 px | 0 tras Fase 0 (torneo incluido) | 0 en todas las rutas |
| `critical`/`serious` de axe | 0 en 12 pantallas | 0 en 15 pantallas |
| Controles <44 px en táctil | Quedan iconos de póker, selects y perfil | 0 |
| Texto de UI <12 px | Nav y botones a 8–10 px | 0 |
| `h1` por pantalla | 2 de 11 | 11 de 11 |
| Initial bundle | 373.59 kB (105.52 kB transfer) | ≤420 kB raw, sin crecer >10 % por PR |
| LCP (4G simulada) | Sin medir | <2.5 s |
| CLS | Sin medir | <0.1 |
| INP en mesa | Sin medir | <200 ms |
| Textos fuera de i18n | `WINS`, `VS` | 0 |
| Cabeceras de juego duplicadas | 5 | 0 |

---

## 12. Qué NO hacer

- **No convertir esto en un SaaS genérico.** El arcade neón es la marca; el problema es la
  legibilidad, no el estilo.
- **No meter una librería de UI entera** (Material, PrimeNG) para arreglar cuatro botones. El
  design system propio ya existe; hay que completarlo.
- **No animar todo.** El movimiento debe explicar un cambio de estado, no decorar.
- **No usar modales dentro de contenedores con `transform`.** Es la receta del “modal en la esquina”.
- **No arreglar el layout con `!important`.** El bug F-01 se arregla con `padding-block`, no con
  fuerza bruta.
- **No copiar dark patterns** (temporizadores, cofres, FOMO). La retención va por jugar con amigos
  y mejorar, como ya se decidió en `docs/INSPIRACION_POKER.md`.
- **No prometer rendimiento sin medirlo.** Lighthouse y presupuesto antes de decir “rápido”.

---

## 13. Anexos

### 13.1 Archivos tocados en la Fase 0

```
front/src/app/features/games/brisca/brisca.scss
front/src/app/features/games/mentiroso/mentiroso.scss
front/src/app/features/games/culo/culo.scss
front/src/app/features/game/tournament/tournament.html
front/src/app/features/game/tournament/tournament.scss
front/src/app/shared/components/header/header.scss
front/src/app/shared/components/button/button.scss
front/src/app/features/home/home.scss
front/public/i18n/es.json
front/public/i18n/en.json
front/public/i18n/fr.json
```

### 13.2 Comandos de verificación

```bash
cd front
npx ng build --configuration production
npx ng test --watch=false
npm run lint
npx playwright test --project=chromium e2e/a11y.spec.ts
npx playwright test --project=chromium e2e/games.spec.ts e2e/tournaments.spec.ts
```

### 13.3 Checklist de PR visual

- [ ] La pantalla tiene un `h1` y el orden de headings es correcto.
- [ ] No hay scroll horizontal a 320, 390, 768, 1024 y 1440 px.
- [ ] Los controles miden ≥44 px en táctil y se pueden usar con teclado.
- [ ] El foco se ve y no se pierde al abrir/cerrar diálogos.
- [ ] Los estados loading/empty/error existen y no dependen solo del color.
- [ ] Los textos están en ES/EN/FR; no hay cadenas fijas.
- [ ] Se respetan tokens de color, spacing y radios; no hay hex nuevos sin justificar.
- [ ] `prefers-reduced-motion` y el ajuste manual siguen funcionando.
- [ ] Build, unitarios, lint y axe en verde.
- [ ] Captura antes/después adjunta en el PR.

### 13.4 Referencias internas

- `docs/ROADMAP_UX.md` — acercamientos A/B/C y decisión de diseño.
- `docs/INSPIRACION_POKER.md` — patrones de producto y plan por tandas.
- `docs/DEVELOPMENT.md` — entorno y comandos.
- `front/src/styles.scss` — tokens y utilidades globales.
- `front/e2e/a11y.spec.ts` — red de seguridad de accesibilidad.
- `front/e2e/helpers.ts` — login simulado para auditorías sin backend.
