// Verifica que el sistema de ficheros del juego persiste al recargar (roadmap 6.1).
//
// Hace lo mismo que hace el juego al guardar la tabla de highscores —escribir en
// `/persist` y pedir `FS.syncfs`— pero con un fichero de prueba, recarga la página y
// comprueba que el contenido sigue ahí. Se ejecuta con Edge headless + CDP, igual que
// `probe_wasm.js`.
//
//   node probe_wasm_persistencia.js https://localhost:8443/game-embed/index.html
const { spawn } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const http = require('http');

const URL_GAME = process.argv[2] || 'http://localhost:8099/index.html';
const CANDIDATES = [
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
];
const BROWSER = CANDIDATES.find((p) => fs.existsSync(p));
if (!BROWSER) { console.error('No encuentro Edge/Chrome'); process.exit(2); }
console.log('navegador:', BROWSER);
console.log('juego:', URL_GAME);

const PROFILE = path.join(os.tmpdir(), 'hermes_wasm_persist_' + Date.now());
const PORT = 9344;
const proc = spawn(BROWSER, [
  '--headless=new', '--disable-gpu', '--enable-unsafe-swiftshader',
  // El stack sirve por HTTPS con certificado autofirmado.
  '--ignore-certificate-errors',
  '--remote-debugging-port=' + PORT, '--user-data-dir=' + PROFILE,
  '--no-first-run', '--no-default-browser-check', '--disable-extensions',
  '--window-size=1280,720', 'about:blank',
], { stdio: 'ignore' });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const getJSON = (u) => new Promise((res, rej) => {
  http.get(u, (r) => { let d = ''; r.on('data', (c) => (d += c)); r.on('end', () => { try { res(JSON.parse(d)); } catch (e) { rej(e); } }); }).on('error', rej);
});

const MARCA = 'persistencia-' + Date.now();
const FICHERO = '/persist/prueba_persistencia.txt';
let fallos = 0;
const check = (ok, texto) => { console.log(`  [${ok ? 'PASS' : 'FALLO'}] ${texto}`); if (!ok) fallos++; };

(async () => {
  let targets = null;
  for (let i = 0; i < 60; i++) {
    try { targets = await getJSON(`http://127.0.0.1:${PORT}/json/list`); if (targets.length) break; } catch (e) {}
    await sleep(500);
  }
  if (!targets || !targets.length) { console.error('CDP no respondió'); proc.kill(); process.exit(3); }
  const page = targets.find((t) => t.type === 'page') || targets[0];

  const ws = new WebSocket(page.webSocketDebuggerUrl);
  let id = 0;
  const pending = new Map();
  const logs = [];
  ws.onmessage = (e) => {
    const m = JSON.parse(e.data);
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); return; }
    if (m.method === 'Log.entryAdded') logs.push(`[${m.params.entry.level}] ${m.params.entry.text}`);
    if (m.method === 'Runtime.exceptionThrown') logs.push('[exception] ' + (m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text));
  };
  const send = (method, params = {}) => new Promise((res) => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
  await new Promise((r) => (ws.onopen = r));

  const evaluar = async (expr) => {
    const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
    return r.result?.result?.value;
  };
  const cargarJuego = async (primera) => {
    const r = await send('Page.navigate', { url: URL_GAME });
    if (primera) console.log('  · navigate ->', JSON.stringify(r.result || r));
    await sleep(12000);   // margen: wasm + 14 MB de assets + arranque del bucle
    const donde = await evaluar('location.href + " | " + document.title + " | canvas:" + !!document.querySelector("canvas")');
    console.log('  · página:', donde);
  };

  await send('Runtime.enable'); await send('Log.enable'); await send('Page.enable');

  // ── 1. arranca y monta /persist ─────────────────────────────────────────
  await cargarJuego(true);
  // El sistema de ficheros se llama `FS` en el pegamento de Emscripten (y suele estar
  // también en `Module.FS`): se acepta cualquiera de los dos.
  const FS = '(typeof FS !== "undefined" ? FS : (Module && Module.FS))';
  check(await evaluar(`!!${FS}`), 'el sistema de ficheros (FS) está accesible');
  check(await evaluar(`!!${FS}.analyzePath("/persist").exists`), 'el directorio /persist está montado');

  // ── 2. escribir y pedir el volcado a IndexedDB ──────────────────────────
  const escrito = await evaluar(`(function () {
    try {
      ${FS}.writeFile(${JSON.stringify(FICHERO)}, ${JSON.stringify(MARCA)});
      ${FS}.syncfs(false, function (err) { window.__syncDone = err ? ('error: ' + err) : 'ok'; });
      return 'escrito';
    } catch (e) { return 'error: ' + e.message; }
  })()`);
  check(escrito === 'escrito', `se escribe ${FICHERO} (${escrito})`);
  await sleep(2500);
  const sync = await evaluar('window.__syncDone || "sin respuesta"');
  check(sync === 'ok', `FS.syncfs vuelca a IndexedDB (${sync})`);

  // ── 3. recargar y comprobar que sigue ahí ───────────────────────────────
  await cargarJuego();
  const leido = await evaluar(`(function () {
    try {
      if (!${FS}.analyzePath(${JSON.stringify(FICHERO)}).exists) return null;
      return ${FS}.readFile(${JSON.stringify(FICHERO)}, { encoding: 'utf8' });
    } catch (e) { return 'error: ' + e.message; }
  })()`);
  check(leido === MARCA, `tras recargar, el fichero sigue con el mismo contenido (${JSON.stringify(leido)})`);

  // ── 4. el juego sigue arrancando igual ──────────────────────────────────
  const canvas = await evaluar('(function(){const c=document.querySelector("canvas");return c?JSON.stringify({w:c.width,h:c.height,gl:!!(c.getContext("webgl")||c.getContext("webgl2"))}):"sin canvas"})()');
  check(/"gl":true/.test(canvas || ''), `el canvas arranca tras recargar (${canvas})`);

  const errores = logs.filter((l) => l.startsWith('[exception]') || l.startsWith('[error]'));
  check(errores.length === 0, `sin excepciones en consola (${errores.length})`);
  if (errores.length) errores.slice(0, 5).forEach((e) => console.log('     ', e));

  // Limpieza: fuera el fichero de prueba (y su volcado).
  await evaluar(`(function(){try{${FS}.unlink(${JSON.stringify(FICHERO)});${FS}.syncfs(false,function(){});}catch(e){}return 1})()`);

  proc.kill();
  console.log(`\n================ ${fallos === 0 ? 'PERSISTENCIA OK' : fallos + ' FALLOS'} ================`);
  process.exit(fallos === 0 ? 0 : 1);
})();
