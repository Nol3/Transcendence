// Verifica en un navegador real que se puede pedir una mesa de 6 jugadores y que
// la mesa se llena con bots hasta los 6 asientos.
//
//   node scripts/audit/probe_poker_ui_6.js https://localhost:8443 https://localhost:8443
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

function post(url, body, token) {
  return new Promise((resolve, reject) => {
    const data = Buffer.from(JSON.stringify(body));
    const mod = url.startsWith('https') ? https : http;
    const req = mod.request(url, {
      method: 'POST', rejectUnauthorized: false,
      headers: { 'Content-Type': 'application/json', 'Content-Length': data.length,
        ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    }, (res) => {
      let out = ''; res.on('data', (c) => (out += c));
      res.on('end', () => { try { resolve({ status: res.statusCode, body: JSON.parse(out) }); }
                            catch (e) { resolve({ status: res.statusCode, body: out }); } });
    });
    req.on('error', reject); req.write(data); req.end();
  });
}

(async () => {
  const stamp = Date.now();
  const username = `ui6_${stamp}`;
  const reg = await post(`${API}/api/auth/register/`, {
    username, email: `${username}@example.com`, password: 'Zx9!pqLmn42',
  });
  if (reg.status !== 201) { console.error('registro falló', reg); process.exit(3); }
  const token = reg.body.data.tokens.accessToken;
  const user = reg.body.data.user;
  console.log(`usuario de prueba: ${username}`);

  const PROFILE = path.join(os.tmpdir(), 'hermes_poker6_' + stamp);
  const PORT = 9448;
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

  const snapshot = `JSON.stringify({
    url: location.pathname,
    sizes: [...document.querySelectorAll('.stakes__btn')].map(b => b.textContent.trim()),
    active: [...document.querySelectorAll('.stakes__btn.is-active')].map(b => b.textContent.trim()),
    seats: [...document.querySelectorAll('.seat')].map(s => ({
      name: s.querySelector('.seat__name')?.textContent?.trim(),
      stack: s.querySelector('.seat__stack')?.textContent?.trim(),
      isBot: !!s.querySelector('.badge'),
    })),
    hasTable: !!document.querySelector('.felt'),
    searching: !!document.querySelector('.searching'),
  })`;

  let snap = JSON.parse(await evaluate(snapshot));
  check('el lobby ofrece los tamaños de mesa', snap.sizes.join(',').includes('6'),
    JSON.stringify(snap.sizes));

  // Elegir mesa de 6 y entrar en cola
  const elegido = await evaluate(`(() => {
    const b = [...document.querySelectorAll('.stakes__btn')].find(x => x.textContent.trim() === '6');
    if (!b) return null; b.click(); return '6';
  })()`);
  check('se puede elegir mesa de 6', elegido === '6');

  const enCola = await evaluate(`(() => {
    const b = [...document.querySelectorAll('button')].find(x => x.textContent.toLowerCase().includes('buscar'));
    if (!b) return null; b.click(); return b.textContent.trim();
  })()`);
  check('se puede pulsar «Buscar partida»', !!enCola, String(enCola));

  // Esperar a que se complete la mesa con bots (QUEUE_TIMEOUT + margen)
  let listo = null;
  for (let i = 0; i < 40; i++) {
    await sleep(1500);
    snap = JSON.parse(await evaluate(snapshot));
    if (snap.hasTable) { listo = snap; break; }
  }
  check('la mesa se abre sin más humanos', !!listo);
  if (listo) {
    check('la mesa tiene 6 asientos', listo.seats.length === 6,
      JSON.stringify(listo.seats.map((s) => s.name)));
    check('5 asientos son bots', listo.seats.filter((s) => s.isBot).length === 5,
      String(listo.seats.filter((s) => s.isBot).length));
    check('yo aparezco sentado', listo.seats.some((s) => (s.name || '').includes('ui6_')),
      JSON.stringify(listo.seats.map((s) => s.name)));
  }
  check('sin errores de consola', logs.length === 0, logs.slice(0, 2).join(' | '));

  const ok = results.filter(([, o]) => o).length;
  console.log(`\n================ ${ok}/${results.length} comprobaciones OK ================`);
  proc.kill();
  try { fs.rmSync(PROFILE, { recursive: true, force: true, maxRetries: 5 }); } catch (e) {}
  process.exit(ok === results.length ? 0 : 1);
})().catch((e) => { console.error(e); process.exit(1); });
