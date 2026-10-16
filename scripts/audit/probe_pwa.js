// Comprueba que la PWA funciona de verdad (roadmap 7.4): Edge headless + CDP.
//   1) el navegador registra el service worker,
//   2) tras recargar, el service worker controla la página (sin recargar no lo hace:
//      así funciona el ciclo de vida de un service worker),
//   3) hay cachés de ngsw, o sea, la app está cacheada para funcionar sin red,
//   4) el manifiesto se descarga y trae lo que debe (nombre, iconos, idioma).
//
// Uso: node scripts/audit/probe_pwa.js [url]   (por defecto, el stack por HTTPS)
const { spawn } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const http = require('http');

const URL_APP = process.argv[2] || 'https://localhost:8443/';
const CANDIDATES = [
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
];
const BROWSER = CANDIDATES.find((p) => fs.existsSync(p));
if (!BROWSER) { console.error('No encuentro Edge/Chrome'); process.exit(2); }
console.log('navegador:', BROWSER);
console.log('url:', URL_APP);

const PROFILE = path.join(os.tmpdir(), 'hermes_pwa_probe_' + Date.now());
const PORT = 9336;
const proc = spawn(BROWSER, [
  '--headless=new', '--disable-gpu',
  // El stack sirve por HTTPS con certificado autofirmado: sin esto el navegador se
  // queda en el aviso de seguridad y la página nunca carga.
  '--ignore-certificate-errors',
  '--remote-debugging-port=' + PORT, '--user-data-dir=' + PROFILE,
  '--no-first-run', '--no-default-browser-check', '--disable-extensions',
  '--window-size=1280,720', 'about:blank',
], { stdio: 'ignore' });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const getJSON = (u) => new Promise((res, rej) => {
  http.get(u, (r) => { let d = ''; r.on('data', (c) => (d += c)); r.on('end', () => { try { res(JSON.parse(d)); } catch (e) { rej(e); } }); }).on('error', rej);
});

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

  await send('Runtime.enable'); await send('Log.enable'); await send('Page.enable');

  const evaluar = async (expr) => {
    const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
    if (r.result?.exceptionDetails) return { error: r.result.exceptionDetails.text };
    return r.result?.result?.value;
  };

  // ── 1) primera carga: se registra el service worker ──────────────────────
  await send('Page.navigate', { url: URL_APP });
  await sleep(9000);
  const primera = await evaluar(`(async () => {
    const regs = await navigator.serviceWorker.getRegistrations();
    const link = document.querySelector('link[rel=manifest]');
    let manifiesto = null;
    if (link) { try { manifiesto = await (await fetch(link.href)).json(); } catch (e) { manifiesto = 'error: ' + e.message; } }
    return JSON.stringify({
      titulo: document.title,
      registros: regs.length,
      alcances: regs.map((r) => r.scope),
      controlada: !!navigator.serviceWorker.controller,
      manifiesto,
    });
  })()`);

  // ── 2) recarga: el service worker pasa a controlar y cachea ──────────────
  await send('Page.reload', { ignoreCache: false });
  await sleep(8000);
  const segunda = await evaluar(`(async () => {
    const claves = await caches.keys();
    return JSON.stringify({
      controlada: !!navigator.serviceWorker.controller,
      caches: claves,
    });
  })()`);

  console.log('\n=== 1) primera carga ===');
  console.log(primera);
  console.log('\n=== 2) tras recargar ===');
  console.log(segunda);

  const p = primera ? JSON.parse(primera) : {};
  const s = segunda ? JSON.parse(segunda) : {};
  const man = p.manifiesto && typeof p.manifiesto === 'object' ? p.manifiesto : null;

  const comprobaciones = [
    ['el service worker se registra', (p.registros ?? 0) >= 1],
    ['tras recargar, controla la página', s.controlada === true],
    ['hay cachés de la app', Array.isArray(s.caches) && s.caches.some((c) => c.includes('ngsw'))],
    ['el manifiesto se descarga', !!man],
    ['el manifiesto tiene nombre', !!man && man.name === 'Transcendence — póker online'],
    ['el manifiesto trae iconos', !!man && Array.isArray(man.icons) && man.icons.length >= 2],
    ['el manifiesto está en español', !!man && man.lang === 'es'],
    ['la página carga el título', /Transcendence/i.test(p.titulo || '')],
  ];

  console.log('\n=== comprobaciones ===');
  let fallos = 0;
  for (const [nombre, ok] of comprobaciones) {
    console.log(`${ok ? '✓' : '✗'} ${nombre}`);
    if (!ok) fallos++;
  }

  const errores = logs.filter((l) => /\[(error|exception)\]/.test(l));
  if (errores.length) {
    console.log('\n=== avisos del navegador ===');
    errores.slice(0, 8).forEach((l) => console.log('  ' + l.slice(0, 160)));
  }

  console.log(`\n${comprobaciones.length - fallos}/${comprobaciones.length} comprobaciones OK`);
  ws.close();
  proc.kill();
  process.exit(fallos ? 1 : 0);
})().catch((e) => { console.error('fallo del sondeo:', e); proc.kill(); process.exit(4); });
