# Poker Race - Deployment & Embedding Guide

## Compilación Web

```bash
# WSL / Linux
source ~/emsdk/emsdk_env.sh
cd /mnt/c/Users/aleja/Desktop/claude/RayLib/Juego\ de\ cartas

# Compilar raylib para web (solo primera vez)
make build-raylib-web

# Compilar el juego
rm -rf web && mkdir web && make web
```

Archivos en `web/` — súbelo a cualquier hosting estático.

---

## Opciones de Hosting (todas gratuitas)

### 1. GitHub Pages (más fácil)
```bash
# Crear repo en GitHub, pushear el proyecto
git init
git add .
git commit -m "feat: poker race web build"
git remote add origin https://github.com/TU_USUARIO/poker-race.git
git push -u origin main

# En GitHub: Settings → Pages → Source: Deploy from branch "gh-pages"
# Automáticamente genera: https://TU_USUARIO.github.io/poker-race/
```

### 2. Cloudflare Pages (mejor rendimiento, ilimitado)
1. Crea cuenta en [dash.cloudflare.com](https://dash.cloudflare.com)
2. Workers and Pages → Create a project → Connect to Git
3. Selecciona tu repo de GitHub
4. Build command: `make web` (necesitas Emscripten en el build)
5. Output directory: `web`
6. Deploy

**Ventajas**: CDN global, HTTPS automático, ilimitado, dominio gratis.

### 3. Netlify (drag & drop sin Git)
1. [app.netlify.com](https://app.netlify.com)
2. Drag & drop la carpeta `web/` directamente
3. Obtén URL: `https://random-name.netlify.app`

### 4. Vercel
```bash
npm i -g vercel
cd web
vercel --prod
```

### 5. Self-hosted (tu propio servidor)
Sube la carpeta `web/` a cualquier servidor nginx/apache:
```bash
scp -r web/* user@server:/var/www/poker-race/
```

---

## Embedding en Otra Web (iframe)

### Opción A: Embedding Simple
```html
<iframe
  src="https://TU_URL.com/"
  width="1280"
  height="720"
  style="border: none; max-width: 100%;"
  allow="fullscreen; gamepad; pointer-lock"
></iframe>
```

### Opción B: Embedding con Comunicación (postMessage)
El juego expone `window.PokerRaceAPI` y envía eventos al parent:

```html
<!-- En tu web: -->
<iframe
  id="poker-game"
  src="https://TU_URL.com/"
  width="1280"
  height="720"
  style="border: none;"
></iframe>

<script>
const gameFrame = document.getElementById('poker-game');

window.addEventListener('message', (event) => {
  if (!event.data || event.data.source !== 'poker-race') return;

  const { type, value, score, round } = event.data;

  switch (type) {
    case 'poker-race-ready':
      console.log('Juego cargado y listo');
      break;
    case 'player-turn':
      console.log(`Turno del jugador ${event.data.index}: ${event.data.player}`);
      break;
    case 'round-end':
      console.log(`Ronda ${round} terminada`);
      break;
    case 'gameover':
      console.log(`JUEGO TERMINADO — Score: ${score}`);
      // Mostrar modal, guardar en DB, lo que necesites
      break;
  }
});

function pauseGame() {
  gameFrame.contentWindow.postMessage({ type: 'pause' }, '*');
}
function resumeGame() {
  gameFrame.contentWindow.postMessage({ type: 'resume' }, '*');
}
function setVolume(master, music, sfx) {
  gameFrame.contentWindow.postMessage({
    type: 'setVolume',
    master, music, sfx
  }, '*');
}
function restartGame() {
  gameFrame.contentWindow.postMessage({ type: 'restart' }, '*');
}
</script>
```

### Opción C: Integración con API
Si tu web tiene backend, usa los eventos para guardar scores:

```javascript
// Guardar high score en tu API cuando termina el juego
window.addEventListener('message', async (event) => {
  if (event.data?.type === 'gameover') {
    await fetch('/api/scores', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        score: event.data.score,
        winner: event.data.winner,
        date: new Date().toISOString()
      })
    });
  }
});
```

### Opción D: Embeber como Componente React/Vue
```jsx
import { useEffect, useRef } from 'react';

function PokerRaceGame({ onGameOver, width = 1280, height = 720 }) {
  const iframeRef = useRef(null);

  useEffect(() => {
    const handler = (event) => {
      if (event.data?.source !== 'poker-race') return;
      if (event.data.type === 'gameover') {
        onGameOver?.(event.data.score);
      }
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, [onGameOver]);

  return (
    <iframe
      ref={iframeRef}
      src={`${process.env.REACT_APP_GAME_URL}/`}
      width={width}
      height={height}
      style={{ border: 'none', maxWidth: '100%' }}
    />
  );
}
```

---

## Compartir Resultado

El juego ya notifica al parent via `postMessage` cuando termina.
Para compartir a redes sociales, intercepta el evento `gameover`:

```javascript
window.addEventListener('message', (event) => {
  if (event.data?.type === 'gameover') {
    const text = `¡He conseguido ${event.data.score} puntos en Poker Race! 🎴`;
    const url = encodeURIComponent(text);
    // WhatsApp
    window.open(`https://wa.me/?text=${url}`, '_blank');
    // Twitter/X
    window.open(`https://twitter.com/intent/tweet?text=${url}`, '_blank');
    // Telegram
    window.open(`https://t.me/share/url?url=${url}`, '_blank');
  }
});
```

---

## Configurar Dominio Personalizado

### Cloudflare Pages
1. Pages → Tu proyecto → Custom domains
2. Añade tu dominio (ej: `juego.tudominio.com`)
3. Cloudflare genera SSL automáticamente

### GitHub Pages
1. Settings → Pages → Custom domain: `juego.tudominio.com`
2. Configura DNS en tu registrador:
   - CNAME: `juego` → `TU_USUARIO.github.io`

---

## Notas Técnicas

- **Ancho de banda**: Ilimitado en Cloudflare Pages. 100 GB/mes en Vercel/Netlify.
- **Tamaño max archivo**: 25 MiB en Cloudflare, sin límite en Netlify.
- **HTTPS**: Automático en todos.
- ** builds/mes**: 500 Cloudflare, 300 min Netlify, 6,000 min Vercel.
- **Texturas/audio**: Los assets se copian automáticamente a `web/` durante la compilación.