// Verifica la customización del póker online (5.5) en un navegador real:
// se elige un tema en el lobby, se comprueba que el servidor lo guarda y que la
// mesa se pinta con ese tema al abrirse.
//
//   node scripts/audit/probe_poker_theme.js https://localhost:8443 https://localhost:8443
const { spawn } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const http = require('http');
const https = require('https');

const APP = process.argv[2] || 'http://localhost:4200';
const API = process.argv[3] || 'http://localhost:8000';
const CANDIDATES = [
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
];
const BROWSER = CANDIDATES.find((p) => fs.existsSync(p));
if (!BROWSER) { console.error('No encuentro Edge/Chrome'); process.exit(2); }
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function request(method, url, body, token) {
  return new Promise((resolve, reject) => {
    const data = body ? Buffer.from(JSON.stringify(body)) : null;
    const mod = url.startsWith('https') ? https : http;
    const headers = { 'Content-Type': 'application/json' };
    if (data) headers['Content-Length'] = data.length;
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const req = mod.request(url, { method, rejectUnauthorized: false, headers }, (res) => {
      let out = ''; res.on('data', (c) => (out += c));
      res.on('end', () => { try { resolve({ status: res.statusCode, body: JSON.parse(out) }); }
                            catch (e) { resolve({ status: res.statusCode, body: out }); } });
    });
    req.on('error', reject);
    if (data) req.write(data);
    req.end();
  });
}

(async () => {
  const stamp = Date.now();
  const username = `tema_${stamp}`;
  const reg = await request('POST', `${API}/api/auth/register/`, {
    username, email: `${username}@example.com`, password: 'Zx9!pqLmn42',
  });
  if (reg.status !== 201) { console.error('registro falló', reg); process.exit(3); }
  const token = reg.body.data.tokens.accessToken;
  const user = reg.body.data.user;
  console.log(`usuario: ${username}`);

  const antes = await request('GET', `${API}/api/poker/preferences/`, null, token);
  console.log(`preferencias iniciales: ${JSON.stringify(antes.body)}`);

  const PROFILE = path.join(os.tmpdir(), 'hermes_tema_' + stamp);
  const PORT = 9452;
  const proc = spawn(BROWSER, [
    '--headless=new', '--disable-gpu', '--enable-unsafe-swiftshader',
    `--remote-debugging-port=${PORT}`, `--user-data-dir=${PROFILE}`,
    '--no-first-run', '--no-default-browser-check', '--ignore-certificate-errors',
    '--window-size=1400,1000', 'about:blank',
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

  await send('Page.navigate', { url: `${APP}/` });
  await sleep(6000);
  await evaluate(`localStorage.setItem('access_token', ${JSON.stringify(token)});
                  localStorage.setItem('current_user', ${JSON.stringify(JSON.stringify(user))});
                  localStorage.setItem('transcendence_lang', 'es'); 'ok'`);
  await send('Page.navigate', { url: `${APP}/poker` });
  await sleep(7000);

  const snap = `JSON.stringify({
    swatches: [...document.querySelectorAll('.themes__swatch')].map(b => b.getAttribute('aria-label')),
    activo: document.querySelector('.themes__swatch.is-active')?.getAttribute('aria-label') ?? null,
    felt: document.querySelector('.felt')?.className ?? null,
    hasTable: !!document.querySelector('.felt'),
  })`;

  let s = JSON.parse(await evaluate(snap));
  check('el lobby ofrece los 5 temas', (s.swatches || []).length === 5, JSON.stringify(s.swatches));
  check('el tema activo es el de por defecto', s.activo === 'classic', String(s.activo));

  // Elegir «neon»
  await evaluate(`document.querySelector('.themes__swatch[aria-label="neon"]')?.click()`);
  await sleep(2000);
  s = JSON.parse(await evaluate(snap));
  check('al pulsar el tema queda marcado en la UI', s.activo === 'neon', String(s.activo));

  const guardado = await request('GET', `${API}/api/poker/preferences/`, null, token);
  check('el servidor guardó el tema', guardado.body?.theme === 'neon',
    JSON.stringify(guardado.body));

  // Recargar: el tema debe seguir puesto (viene del servidor)
  await send('Page.navigate', { url: `${APP}/poker` });
  await sleep(7000);
  s = JSON.parse(await evaluate(snap));
  check('al recargar la página el tema sigue puesto', s.activo === 'neon', String(s.activo));

  // Entrar en una mesa: el tapete se pinta con el tema
  await evaluate(`(() => {
    const b = [...document.querySelectorAll('button')].find(x => x.textContent.toLowerCase().includes('buscar'));
    b?.click(); return !!b;
  })()`);
  let mesa = null;
  for (let i = 0; i < 30; i++) {
    await sleep(1500);
    s = JSON.parse(await evaluate(snap));
    if (s.hasTable) { mesa = s; break; }
  }
  check('la mesa se abre (bot tras la espera)', !!mesa);
  if (mesa) {
    check('el tapete usa el tema guardado', (mesa.felt || '').includes('felt--neon'),
      String(mesa.felt));
  }
  check('sin errores de consola', logs.length === 0, logs.slice(0, 2).join(' | '));

  const ok = results.filter(([, o]) => o).length;
  console.log(`\n================ ${ok}/${results.length} comprobaciones OK ================`);
  proc.kill();
  try { fs.rmSync(PROFILE, { recursive: true, force: true, maxRetries: 5 }); } catch (e) {}
  process.exit(ok === results.length ? 0 : 1);
})().catch((e) => { console.error(e); process.exit(1); });
