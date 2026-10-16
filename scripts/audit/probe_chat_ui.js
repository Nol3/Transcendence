// Verifica la página de chat en un navegador real contra el stack desplegado:
// A escribe a B por API, B abre /chat, ve la conversación, responde por la UI y
// se comprueba por API que la respuesta ha llegado.
//
//   node scripts/audit/probe_chat_ui.js https://localhost:8443 https://localhost:8443
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

function req(method, url, body, token) {
  return new Promise((resolve, reject) => {
    const data = body ? Buffer.from(JSON.stringify(body)) : null;
    const mod = url.startsWith('https') ? https : http;
    const headers = { 'Content-Type': 'application/json' };
    if (data) headers['Content-Length'] = data.length;
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const r = mod.request(url, { method, rejectUnauthorized: false, headers }, (res) => {
      let out = '';
      res.on('data', (c) => (out += c));
      res.on('end', () => {
        try { resolve({ status: res.statusCode, body: JSON.parse(out) }); }
        catch (e) { resolve({ status: res.statusCode, body: out }); }
      });
    });
    r.on('error', reject);
    if (data) r.write(data);
    r.end();
  });
}

const post = (url, body, token) => req('POST', url, body, token);
const get = (url, token) => req('GET', url, null, token);

(async () => {
  // 1) Dos usuarios y un mensaje de A a B
  const stamp = Date.now();
  const registrar = async (etiqueta) => {
    const username = `chat_${etiqueta}_${stamp}`;
    const r = await post(`${API}/api/auth/register/`, {
      username, email: `${username}@example.com`, password: 'Zx9!pqLmn42',
    });
    if (r.status !== 201) { console.error('registro falló', r); process.exit(3); }
    return { token: r.body.data.tokens.accessToken, user: r.body.data.user };
  };
  const a = await registrar('a');
  const b = await registrar('b');
  console.log(`A=${a.user.username} (#${a.user.id})  B=${b.user.username} (#${b.user.id})`);

  const enviado = await post(`${API}/api/chat/messages/send_message/`,
    { recipient_id: b.user.id, content: '¿jugamos un torneo?' }, a.token);
  if (enviado.status !== 201) { console.error('envío falló', enviado); process.exit(4); }

  // 2) Navegador real con la sesión de B
  const PROFILE = path.join(os.tmpdir(), 'hermes_chat_ui_' + stamp);
  const PORT = 9446;
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
    if (m.method === 'Runtime.exceptionThrown') logs.push('[exception] ' + (m.params.exceptionDetails.exception?.description || '').slice(0, 200));
    if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') logs.push('[console.error] ' + m.params.args.map((x) => x.value ?? x.description ?? '').join(' ').slice(0, 200));
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

  const HELPERS = `
    window.__snap = () => JSON.stringify({
      url: location.pathname,
      convs: [...document.querySelectorAll('.convs__item')].map(b => b.textContent.replace(/\\s+/g, ' ').trim()),
      unread: [...document.querySelectorAll('.convs__badge')].map(b => b.textContent.trim()),
      thread: [...document.querySelectorAll('.thread__bubble')].map(b => b.textContent.replace(/\\s+/g, ' ').trim()),
      activeTitle: document.querySelector('app-card h3, app-card .card__title')?.textContent?.trim() ?? null,
      hasCompose: !!document.querySelector('.compose__input'),
    });
    window.__click = (needle) => {
      const b = [...document.querySelectorAll('button')].find(x => x.textContent.toLowerCase().includes(needle.toLowerCase()));
      if (!b) return null; b.click(); return b.textContent.replace(/\\s+/g, ' ').trim();
    };
    window.__type = (sel, texto) => {
      const el = document.querySelector(sel);
      if (!el) return false;
      const setter = Object.getOwnPropertyDescriptor(el.constructor.prototype, 'value').set;
      setter.call(el, texto);
      el.dispatchEvent(new Event('input', { bubbles: true }));
      return true;
    };`;

  // 3) Abrir /chat con la sesión de B
  await send('Page.navigate', { url: `${APP}/` });
  await sleep(6000);
  await evaluate(`localStorage.setItem('access_token', ${JSON.stringify(b.token)});
                  localStorage.setItem('current_user', ${JSON.stringify(JSON.stringify(b.user))});
                  localStorage.setItem('transcendence_lang', 'es'); 'ok'`);
  await send('Page.navigate', { url: `${APP}/chat` });
  await sleep(7000);
  await evaluate(HELPERS);

  let snap = JSON.parse(await evaluate('window.__snap()'));
  check('la página /chat carga', snap.url === '/chat', `-> url=${snap.url}`);
  check('veo la conversación con A', snap.convs.some((c) => c.includes(a.user.username)),
    JSON.stringify(snap.convs));
  check('veo el último mensaje en la lista', snap.convs.some((c) => c.includes('¿jugamos un torneo?')),
    JSON.stringify(snap.convs));
  check('el mensaje sin leer sale marcado', snap.unread.includes('1'), JSON.stringify(snap.unread));

  // 4) Abrir la conversación y responder por la UI
  const abierto = await evaluate(`window.__click(${JSON.stringify(a.user.username)})`);
  await sleep(1500);
  snap = JSON.parse(await evaluate('window.__snap()'));
  check('al abrirla se ve el hilo', snap.thread.some((t) => t.includes('¿jugamos un torneo?')),
    JSON.stringify(snap.thread));
  check('hay caja para escribir', snap.hasCompose);

  const texto = `voy para la mesa ${stamp}`;
  await evaluate(`window.__type('.compose__input', ${JSON.stringify(texto)})`);
  await sleep(300);
  await evaluate(`window.__click('ENVIAR') ?? window.__click('Enviar')`);
  await sleep(2500);

  snap = JSON.parse(await evaluate('window.__snap()'));
  check('mi respuesta aparece en el hilo', snap.thread.some((t) => t.includes(texto)),
    JSON.stringify(snap.thread));

  // 5) Comprobación por API: A ve la respuesta de B
  const conv = await get(`${API}/api/chat/messages/conversation/?user_id=${b.user.id}`, a.token);
  const textos = Array.isArray(conv.body) ? conv.body.map((m) => m.content) : [];
  check('el servidor tiene la respuesta de B', textos.includes(texto), JSON.stringify(textos));

  const email = JSON.stringify(conv.body).includes('@example.com');
  check('la API del chat no filtra emails', !email);

  check('sin errores de consola', logs.length === 0, logs.slice(0, 2).join(' | '));

  const ok = results.filter(([, o]) => o).length;
  console.log(`\n================ ${ok}/${results.length} comprobaciones OK ================`);
  proc.kill();
  // El navegador puede seguir soltando el perfil: la limpieza no debe romper el
  // resultado de la verificación.
  try { fs.rmSync(PROFILE, { recursive: true, force: true, maxRetries: 5 }); } catch (e) {}
  process.exit(ok === results.length ? 0 : 1);
})().catch((e) => { console.error(e); process.exit(1); });
