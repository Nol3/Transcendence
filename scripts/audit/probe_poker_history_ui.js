// Verifica la página de historial de póker en un navegador real contra el stack.
// Necesita un usuario con historial: lo crea el script seed_poker_history.py.
//
//   node scripts/audit/probe_poker_history_ui.js <usuario> <password> [APP] [API]
const { spawn } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const http = require('http');
const https = require('https');

const USER = process.argv[2];
const PASS = process.argv[3];
const APP = process.argv[4] || 'https://localhost:8443';
const API = process.argv[5] || APP;
if (!USER || !PASS) {
  console.error('uso: node probe_poker_history_ui.js <usuario> <password> [APP] [API]');
  process.exit(2);
}

const CANDIDATES = [
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
];
const BROWSER = CANDIDATES.find((p) => fs.existsSync(p));
if (!BROWSER) { console.error('No encuentro Edge/Chrome'); process.exit(2); }
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function post(url, body) {
  return new Promise((resolve, reject) => {
    const data = Buffer.from(JSON.stringify(body));
    const mod = url.startsWith('https') ? https : http;
    const req = mod.request(url, {
      method: 'POST', rejectUnauthorized: false,
      headers: { 'Content-Type': 'application/json', 'Content-Length': data.length },
    }, (res) => {
      let out = ''; res.on('data', (c) => (out += c));
      res.on('end', () => { try { resolve({ status: res.statusCode, body: JSON.parse(out) }); }
                            catch (e) { resolve({ status: res.statusCode, body: out }); } });
    });
    req.on('error', reject); req.write(data); req.end();
  });
}

(async () => {
  const login = await post(`${API}/api/auth/login/`, { email: USER, password: PASS });
  if (login.status !== 200) { console.error('login falló', login); process.exit(3); }
  const token = login.body.data.tokens.accessToken;
  const user = login.body.data.user;
  console.log(`usuario: ${user.username} (#${user.id})`);

  const PROFILE = path.join(os.tmpdir(), 'hermes_hist_' + Date.now());
  const PORT = 9450;
  const proc = spawn(BROWSER, [
    '--headless=new', '--disable-gpu', '--enable-unsafe-swiftshader',
    `--remote-debugging-port=${PORT}`, `--user-data-dir=${PROFILE}`,
    '--no-first-run', '--no-default-browser-check', '--ignore-certificate-errors',
    '--window-size=1400,1100', 'about:blank',
  ], { stdio: 'ignore' });

  const getJSON = (u) => new Promise((res, rej) => {
    http.get(u, (r) => { let d = ''; r.on('data', (c) => (d += c));
      r.on('end', () => { try { res(JSON.parse(d)); } catch (e) { rej(e); } }); }).on('error', rej);
  });
  let targets = null;
  for (let i = 0; i < 60; i++) {
    try { targets = await getJSON(`http://127.0.0.1:${PORT}/json/list`); if (targets.length) break; } catch (e) {}
    await sleep(500);
  }
  const page = targets.find((t) => t.type === 'page') || targets[0];
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  let id = 0; const pending = new Map(); const logs = [];
  ws.onmessage = (e) => {
    const m = JSON.parse(e.data);
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); return; }
    if (m.method === 'Runtime.exceptionThrown') logs.push('[exception] ' + (m.params.exceptionDetails.exception?.description || '').slice(0, 160));
    if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') logs.push('[console.error] ' + m.params.args.map((x) => x.value ?? x.description ?? '').join(' ').slice(0, 160));
  };
  const send = (method, params = {}) => new Promise((res) => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
  await new Promise((r) => (ws.onopen = r));
  await send('Runtime.enable'); await send('Page.enable');
  const evaluate = async (expr) => {
    const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
    return r.result?.result?.value;
  };

  const results = [];
  const check = (label, ok, detail = '') => { results.push([label, ok, detail]); console.log(`  [${ok ? 'PASS' : 'FAIL'}] ${label} ${detail}`); };

  const snapshot = `JSON.stringify({
    url: location.pathname,
    stats: [...document.querySelectorAll('.stats__row')].map(r => r.textContent.replace(/\\s+/g,' ').trim()),
    matches: [...document.querySelectorAll('.matches__item')].map(m => m.textContent.replace(/\\s+/g,' ').trim()),
    hands: [...document.querySelectorAll('.hand')].map(h => ({
      head: h.querySelector('.hand__head')?.textContent?.replace(/\\s+/g,' ').trim(),
      players: [...h.querySelectorAll('.hand__player')].map(p => p.textContent.replace(/\\s+/g,' ').trim()),
    })),
  })`;

  await send('Page.navigate', { url: `${APP}/` });
  await sleep(6000);
  await evaluate(`localStorage.setItem('access_token', ${JSON.stringify(token)});
                  localStorage.setItem('current_user', ${JSON.stringify(JSON.stringify(user))});
                  localStorage.setItem('transcendence_lang', 'es'); 'ok'`);
  await send('Page.navigate', { url: `${APP}/poker/history` });
  await sleep(8000);

  let snap = JSON.parse(await evaluate(snapshot));
  check('la página de historial carga', snap.url === '/poker/history', `-> ${snap.url}`);
  check('muestra las estadísticas', snap.stats.length >= 4, JSON.stringify(snap.stats.slice(0, 3)));
  check('lista al menos una partida', snap.matches.length >= 1, JSON.stringify(snap.matches[0] ?? ''));
  check('la partida dice contra quién y el resultado',
    /contra/i.test(snap.matches[0] ?? ''), snap.matches[0] ?? '');

  // Abrir la partida → deben salir sus manos
  await evaluate(`document.querySelector('.matches__item')?.click()`);
  await sleep(3000);
  snap = JSON.parse(await evaluate(snapshot));
  check('al abrir la partida salen sus manos', snap.hands.length >= 1, `${snap.hands.length} manos`);
  if (snap.hands.length) {
    check('la mano dice el bote y quién gana',
      /Mano #/.test(snap.hands[0].head ?? '') && /Gana/.test(snap.hands[0].head ?? ''),
      snap.hands[0].head ?? '');
    check('la mano lista a sus jugadores', snap.hands[0].players.length >= 2,
      JSON.stringify(snap.hands[0].players));
  }
  check('sin errores de consola', logs.length === 0, logs.slice(0, 2).join(' | '));

  const ok = results.filter(([, o]) => o).length;
  console.log(`\n================ ${ok}/${results.length} comprobaciones OK ================`);
  proc.kill();
  try { fs.rmSync(PROFILE, { recursive: true, force: true, maxRetries: 5 }); } catch (e) {}
  process.exit(ok === results.length ? 0 : 1);
})().catch((e) => { console.error(e); process.exit(1); });
