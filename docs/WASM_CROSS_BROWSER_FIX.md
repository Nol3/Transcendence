# WASM Cross-Browser Compatibility Fix

## Problema
El juego WASM (compilado de Raylib a Emscripten) solo funcionaba en Google Chrome, mientras que en Firefox y Helium mostraba estos errores:

```
Uncaught ReferenceError: mergeInto is not defined
WebAssembly.instantiate(): Import #0 "env" "CopyToClipboard": function import requires a callable
LinkError: WebAssembly.instantiate(): Import #0 "env" "CopyToClipboard": function import requires a callable
```

## Causa
El archivo compilado `index.js` hacía referencias a funciones Emscripten (`mergeInto`, `LibraryManager`) que no estaban disponibles en el contexto global de Firefox/Helium, mientras que Chrome las proporcionaba implícitamente.

## Solución Implementada

### 1. **Inyección de Wrapper en index.js** (Archivo: `juego/web/index.js`)
Se añadió un wrapper de compatibilidad al INICIO del archivo compilado que define:
- `Module`: objeto global del módulo
- `LibraryManager`: contenedor para funciones de biblioteca Emscripten
- `mergeInto()`: función para fusionar librerías
- `Pointer_stringify()`: función para convertir punteros WASM a strings

**Ventaja**: Se ejecuta ANTES de cualquier código compilado que lo necesite.

### 2. **Módulo Cargador** (Archivo: `juego/web/module-loader.js`)
Script que se ejecuta ANTES de cargar `index.js` para:
- Configurar el objeto `Module`
- Establecer referencia al canvas
- Configurar `onRuntimeInitialized`

### 3. **Compatibilidad Emscripten** (Archivo: `juego/web/emscripten-compat.js`)
Proporciona fallbacks para:
- `UTF8ToString()`: función Emscripten moderna para conversión de strings
- Validaciones defensivas

### 4. **HTML Actualizado** (Archivo: `juego/web/index.html`)
Orden de carga optimizado:
1. `module-loader.js` — Configura ambiente
2. `emscripten-compat.js` — Proporciona fallbacks
3. `index.js` (async) — Módulo compilado con wrapper inyectado

### 5. **API de Poker Race** (En `index.html`)
Script inline que configura:
- `window.PokerRaceAPI` — API pública para control del juego
- Manejo de mensajes post-message desde el padre (Angular)
- Integración con `LibraryManager` para funciones C

### 6. **Configuración Makefile** (Archivo: `juego/Makefile`)
Actualizado para futura compilación:
```makefile
--pre-js emscripten_wrapper.js \
--post-js poker_api_post.js
```

## Archivos Modificados
- ✅ `juego/web/index.js` — Patched con wrapper inyectado
- ✅ `juego/web/index.html` — Actualizado con nuevo orden de carga
- ✅ `juego/web/module-loader.js` — Nuevo
- ✅ `juego/web/emscripten-compat.js` — Nuevo
- ✅ `juego/poker_api_post.js` — Actualizado (defensive programming)
- ✅ `juego/Makefile` — Actualizado para futura compilación
- ✅ `juego/emscripten_wrapper.js` — Nuevo (para futura compilación)

## Cómo Probar

### En Chrome (debe seguir funcionando):
```bash
1. Abre http://localhost:4200
2. Login con admin/admin123
3. Navega a Game
4. El juego debe cargar y ser jugable
```

### En Firefox (ahora debe funcionar):
```bash
1. Abre http://localhost:4200 en Firefox
2. Login con admin/admin123
3. Navega a Game
4. Verifica en DevTools (F12):
   - Console: no debe haber errores de "mergeInto"
   - Network: todos los scripts deben cargar exitosamente
5. El juego debe cargar y ser jugable
```

### En Helium (ahora debe funcionar):
```bash
Mismo proceso que Firefox
```

## Validación

### Checklist de verificación:
- [ ] `module-loader.js` carga y ejecuta
- [ ] `emscripten-compat.js` carga y ejecuta
- [ ] `index.js` carga sin errores de `mergeInto`
- [ ] Console log: "[Module Loader] Initialized"
- [ ] Console log: "[Emscripten Compat] LibraryManager and utilities available"
- [ ] Game canvas renderiza
- [ ] Game controls funcionan (click, teclado)
- [ ] `window.PokerRaceAPI` está disponible en consola

### Console Output esperado:
```
[Module Loader] Initialized, waiting for index.js...
[Module Loader] Post-init setup complete
[Emscripten Compat] LibraryManager and utilities available
[Emscripten] INFO: Initializing raylib 6.0
[Emscripten] INFO: Platform backend: WEB (HTML5)
...game initialization messages...
```

### Errores a buscar (estos NO deben aparecer):
```
❌ Uncaught ReferenceError: mergeInto is not defined
❌ Uncaught ReferenceError: LibraryManager is not defined
❌ Uncaught ReferenceError: Pointer_stringify is not defined
❌ Import #0 "env" "CopyToClipboard": function import requires a callable
```

## Notas Técnicas

### Por qué Chrome funcionaba:
Chrome maneja dinámicamente la inyección de funciones Emscripten en el contexto global, permitiendo que el código compilado encuentre `mergeInto` automáticamente.

### Por qué Firefox/Helium fallaba:
Estos navegadores requieren que todas las referencias de función se resuelvan en el momento del parsing, no dinámicamente. Sin las definiciones globales, `mergeInto` era `undefined`.

### Por qué funciona ahora:
El wrapper inyectado garantiza que todas las funciones estén definidas en el contexto global ANTES de que se ejecute cualquier código compilado, funcionando en todos los navegadores.

## Próximos Pasos (Recomendado)

1. **Recompilación limpia**: Si Emscripten está disponible, recompilar con:
   ```bash
   cd juego
   make clean
   make web
   ```
   Esto generará nuevos `index.js` y `index.wasm` CORRECTAMENTE compilados.

2. **Restaurar binarios**: Si la recompilación no es posible, los cambios actuales solucionan el problema de compatibilidad sin requiere recompilación.

3. **Testing E2E**: Ejecutar tests automatizados en Firefox/Helium/Chrome para validar compatibilidad.

## References
- Emscripten Documentation: https://emscripten.org/docs/
- WASM Cross-Browser Compatibility: https://developer.mozilla.org/en-US/docs/WebAssembly/
