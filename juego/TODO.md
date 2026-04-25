# Poker Race - TODO del Proyecto

Juego de cartas estilo Balatro simplificado para 2-4 jugadores en modo hot-seat (turnos locales).

---

## ✅ COMPLETADO

### Estructura del Proyecto
- [x] Crear archivos de encabezado (.h) con estructuras de datos
- [x] Implementar sistema de cartas (card.h/c)
- [x] Implementar evaluador de manos de póker completo (poker_hand.h/c)
- [x] Crear sistema de juego con estados (game.h/c)
- [x] Crear renderizador de cartas procedural (renderer.h/c)
- [x] Implementar main.c con loop principal
- [x] Crear Makefile para desktop y web
- [x] Crear minshell.html para versión web

---

## PENDIENTE

### Fase 1: Testing y Correcciones 
- [x] Compilar y probar versión desktop (WSL)
- [x] Verificar detección de todas las manos de póker
- [x] Testear sistema de turnos hot-seat
- [x] Corregir bugs de input/ratón (coordenadas corregidas)
- [x] Ajustar posiciones UI y fondo
- [x] **Fondo negro** `(0, 0, 0)`
- [x] Cartas con fondo blanco (antes eran transparentes)
- [x] Botones agregados en todas las pantallas (CONTINUAR, ESTOY LISTO, SIGUIENTE, JUGAR DE NUEVO)
- [x] **Botón CONTINUAR** funciona correctamente como ENTER
- [x] **Sistema de descarte**: Botón rojo para descartar hasta 5 cartas, 1 vez por turno
- [x] **Jugar con menos cartas**: Ya no requiere exactamente 5 cartas (mínimo 1)
- [x] **Script wsl-run.sh**: Para compilar y ejecutar automáticamente en cualquier PC con WSL

### Fase 2: Mejoras Visuales
- [x] Extraer PNGs corregidos - Script v2 con centrado automático
- [x] 52 cartas por set - 2 sets disponibles:
  - default - Cartas estándar (sufijo: none)
  - alto_contraste - Alto contraste (sufijo: _hc)
- [x] Sistema de texturas implementado con soporte multi-set
- [x] Renderer actualizado con dimensiones correctas (71×95 px)
- [x] Fallback procedural si las texturas no cargan
- [x] Efectos visuales: Sombras y brillo en hover implementados
- [x] Animaciones de reparto - Cartas vuelan desde el mazo central
- [x] Animaciones de selección - Hover con escala animada (1.0 → 1.15x)
- [x] Animación de entrega - Acelerada, necesita ajustar velocidad
- [x] Placeholder carta boca abajo - Textura cargada desde assets

### Fase 3: Compilación Web
- [x] Compilar Raylib para WebAssembly (make build-raylib-web)
- [x] Compilar juego para web (make web)
- [x] Probar en navegador local (make run-web)
- [x] Corregir bugs de runtime web (NODEFS remove, preload-file add)
- [x] Verificar que funciona en móvil/tablet

### UI y Controles
- [x] Botones de configuración de volumen funcionan
- [x] Colores UI - grises a negro, blancas/amarillas a estilo puntuación

### Deploy y Embedding
- [x] Guía de deployment - DEPLOY.md con 5 opciones de hosting gratuito
- [x] API de embedding - window.PokerRaceAPI + window.PokerRaceGame
- [x] Comunicación postMessage - Eventos: gameover, round-end, player-turn, ready
- [x] Botón compartir resultado (copiar a clipboard)
- [x] Pantalla de configuración con controles de volumen

### Fase 5: Comodines (Extensión tipo Balatro)
- [x] Sistema de tienda entre rondas - Tienda con 3 comodines, reroll por $1
- [x] Comodín: Emparejador - +10 pts por cada Pareja
- [x] Comodín: As Dorado - x2 si incluye As
- [x] Comodín: Corazón Rojo - +5 pts por cada carta roja
- [x] Comodín: Colorito - x1.5 si todas son del mismo palo

---

## 📁 Estructura del Proyecto

```
Juego de cartas/
├── src/
│   ├── main.c              # Entry point
│   ├── game.h/c            # Lógica principal y estados
│   ├── card.h/c            # Sistema de cartas y baraja
│   ├── poker_hand.h/c     # Evaluador de manos
│   ├── card_textures.h/c   # Sistema de texturas (multi-set)
│   ├── renderer.h/c        # Renderizado y UI
│   ├── audio.h/c           # Sonidos y música procedural
│   └── joker.h/c          # Sistema de tienda/comodines
├── assets/
│   ├── cards/              # Sprites de cartas (BASIC/, DEFAULT/, 1.cards/)
│   └── audio/              # 8 archivos WAV generadas proceduralmente
├── fonts/                  # Fuentes personalizadas
├── poker_api_post.js       # API de embedding para Emscripten
├── emscripten_api.js       # Glue code para comunicación postMessage
├── DEPLOY.md               # Guía de deployment y embedding
├── build/                  # Ejecutable desktop
├── web/                    # Archivos web (subir a hosting)
├── Makefile                # Compilación desktop + web
└── TODO.md
```

---

## Cómo Jugar

1. **Setup**: Selecciona 2-4 jugadores, presiona CONTINUAR
2. **Reparto**: Cada jugador recibe 8 cartas
3. **Selección**: Elige 1-5 cartas para formar tu mejor mano (máximo 5)
4. **Descarte (opcional)**: Selecciona hasta 5 cartas y presiona DESCARTAR (rojo) para robar nuevas. **Solo 1 vez por turno.**
5. **Confirmar**: Presiona CONFIRMAR o ENTER para jugar tu mano
6. **Evaluación**: El sistema detecta automáticamente tu mano de póker

### Puntuación:
   - Pareja: 10 pts
   - Doble Pareja: 20 pts
   - Trío: 30 pts
   - Escalera: 40 pts
   - Color: 50 pts
   - Full House: 60 pts

### Controles:
   - **Ratón**: Click en cartas para seleccionar/deseleccionar
   - **Botones**: CONTINUAR, CONFIRMAR, DESCARTAR, ESTOY LISTO, SIGUIENTE
   - **Teclado**: ENTER (alternativa a los botones)

---

## Comandos de Compilación

### Windows (con MinGW)
```bash
make desktop
make run
```

### WSL (Windows Subsystem for Linux)
```bash
# Primera vez: compilar raylib para Linux
make build-raylib-linux

# Luego compilar el juego
make desktop
make run
```

### Web (Emscripten)
```bash
make build-raylib-web   # Primera vez
make web                # Compilar juego
make run-web            # Servir en localhost:8080
```

---

## 🎯 Próximos Pasos Inmediatos

1. **Proporcionar assets**: Carpeta `assets/cards/` con PNGs de las 52 cartas
2. **Probar compilación**: Verificar que `make desktop` funciona
3. **Testear gameplay**: Jugar partida completa 2-4 jugadores
4. **Preparar versión web**: Compilar y probar en navegador

---

## 📝 Notas

- **2 sets de cartas disponibles**: Default y Alto Contraste (`_hc`)
- **Tamaño de cartas**: 71×95 px (del sprite sheet)
- **Fallback**: Si las texturas fallan, usa renderizado procedural (♥♦♣♠)
- **Selección visual**: Overlay dorado cuando una carta está seleccionada
- **Hot-seat**: Pantalla de "pasa el dispositivo" entre jugadores
- **Multi-input**: Ratón, teclado y touch soportados

### Cambiar Set de Cartas

Para usar el set de alto contraste, modifica `main.c`:
```c
// En lugar de:
LoadCardTextures(&g_cardTextures);  // Carga set default

// Usa:
LoadCardTexturesSet(&g_cardTextures, CARD_SET_HIGH_CONTRAST);  // Alto contraste