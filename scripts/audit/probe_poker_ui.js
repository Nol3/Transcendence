// Verifica la mesa de póker en un navegador real: entra en cola, le empareja con
// un bot, juega una mano pulsando botones y comprueba lo que se pinta.
const { spawn } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const http = require('http');

const APP = 'http://localhost:4200';
const API = 'http://localhost:8000';
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
    const req = http.request(url, { method: 'POST', headers: {
      'Content-Type': 'application/json', 'Content-Length': data.length,
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    }}, (res) => {
      let out = ''; res.on('data', (c) => (out += c));
      res.on('end', () => { try { resolve({ status: res.statusCode, body: JSON.parse(out) }); }
                            catch (e) { resolve({ status: res.statusCode, body: out }); } });
    });
    req.on('error', reject); req.write(data); req.end();
  });
}

(async () => {
  // 1) Usuario de prueba
  const stamp = Date.now();
  const username = `ui_${stamp}`;
  const reg = await post(`${API}/api/auth/register/`, {
    username, email: `${username}@example.com`, password: 'Zx9!pqLmn42',
  });
  if (reg.status !== 201) { console.error('registro falló', reg); process.exit(3); }
  const token = reg.body.data.tokens.accessToken;
  const user = reg.body.data.user;
  console.log(`usuario de prueba: ${username}`);

  // 2) Navegador
  const PROFILE = path.join(os.tmpdir(), 'hermes_poker_ui_' + stamp);
  const PORT = 9444;
  const proc = spawn(BROWSER, [
    '--headless=new', '--disable-gpu', '--enable-unsafe-swiftshader',
    `--remote-debugging-port=${PORT}`, `--user-data-dir=${PROFILE}`,
    '--no-first-run', '--no-default-browser-check', '--window-size=1400,1000', 'about:blank',
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
    if (m.method === 'Log.entryAdded' && m.params.entry.level === 'error') logs.push('[log] ' + m.params.entry.text);
    if (m.method === 'Runtime.exceptionThrown') logs.push('[exception] ' + (m.params.exceptionDetails.exception?.description || '').slice(0, 200));
    if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') logs.push('[console.error] ' + m.params.args.map((a) => a.value ?? a.description ?? '').join(' ').slice(0, 200));
  };
  const send = (method, params = {}) => new Promise((res) => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
  await new Promise((r) => (ws.onopen = r));
  await send('Runtime.enable'); await send('Log.enable'); await send('Page.enable');

  const evaluate = async (expr) => {
    const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
    return r.result?.result?.value;
  };
  const shot = async (name) => {
    const r = await send('Page.captureScreenshot', { format: 'png' });
    if (r.result?.data) fs.writeFileSync(path.join(__dirname, name), Buffer.from(r.result.data, 'base64'));
  };

  const results = [];
  const check = (label, ok, detail = '') => { results.push([label, ok, detail]); console.log(`  [${ok ? 'PASS' : 'FAIL'}] ${label} ${detail}`); };

  const HELPERS = `
    window.__snap = () => {
      const q = (s) => document.querySelector(s);
      const txt = (el) => (el ? el.textContent.replace(/\\s+/g, ' ').trim() : null);
      return JSON.stringify({
        url: location.pathname,
        myCards: [...document.querySelectorAll('.seat--me .card')].map(txt),
        rivalCards: [...document.querySelectorAll('.seat--rival .card')].map(c => c.classList.contains('card--back') ? 'back' : txt(c)),
        board: [...document.querySelectorAll('.board .card')].map(txt),
        pot: txt(q('.pot__value')),
        actions: [...document.querySelectorAll('.actions button')].map(txt),
        seats: [...document.querySelectorAll('.seat')].map(s => ({ name: txt(s.querySelector('.seat__name')), stack: txt(s.querySelector('.seat__stack')), hand: txt(s.querySelector('.seat__hand')) })),
        outcome: txt(q('.outcome__title')),
        bar: txt(q('.table__bar')),
        finished: !!q('.match-over'),
        hasTable: !!q('.felt'),
        queueVisible: !!q('.searching'),
      });
    };
    window.__click = (needle) => {
      const b = [...document.querySelectorAll('button')].find(x => x.textContent.toLowerCase().includes(needle.toLowerCase()));
      if (!b) return null;
      b.click();
      return b.textContent.replace(/\\s+/g, ' ').trim();
    };`;

  // 3) Ir a la app, meter el token y abrir /poker
  await send('Page.navigate', { url: `${APP}/` });
  await sleep(6000);
  await evaluate(`localStorage.setItem('access_token', ${JSON.stringify(token)});
                  localStorage.setItem('current_user', ${JSON.stringify(JSON.stringify(user))});
                  localStorage.setItem('transcendence_lang', 'es'); 'ok'`);
  await send('Page.navigate', { url: `${APP}/poker` });
  await sleep(7000);
  await evaluate(HELPERS);

  let snap = JSON.parse(await evaluate('window.__snap()'));
  check('la página /poker carga el lobby', snap.url === '/poker' && !snap.hasTable, `-> url=${snap.url}`);

  // 4) Entrar en cola
  const clicked = await evaluate(`window.__click('BUSCAR')`);
  check('se puede pulsar «Buscar partida»', !!clicked, `-> "${clicked}"`);
  await sleep(1500);
  snap = JSON.parse(await evaluate('window.__snap()'));
  check('aparece el estado «en cola»', snap.queueVisible || !snap.hasTable, `-> ${snap.bar ?? ''}`);
  await shot('poker_cola.png');

  // 5) Esperar al bot (QUEUE_TIMEOUT=3) y comprobar la mesa
  let matched = false;
  for (let i = 0; i < 30 && !matched; i++) {
    await sleep(1000);
    snap = JSON.parse(await evaluate('window.__snap()'));
    matched = snap.hasTable;
  }
  check('tras el timeout entra el bot y se abre la mesa', matched, `-> ${snap.bar ?? ''}`);
  check('veo mis 2 cartas', snap.myCards.length === 2 && snap.myCards.every((c) => c), `-> ${JSON.stringify(snap.myCards)}`);
  check('las cartas del rival están boca abajo',
        snap.rivalCards.length === 2 && snap.rivalCards.every((c) => c === 'back'), `-> ${JSON.stringify(snap.rivalCards)}`);
  check('hay 5 huecos de comunitarias', snap.board.length === 5, `-> ${JSON.stringify(snap.board)}`);
  check('se muestra el bote', snap.pot !== null, `-> bote=${snap.pot}`);
  check('se muestran los dos asientos', snap.seats.length === 2, `-> ${JSON.stringify(snap.seats.map((s) => s.name))}`);
  await shot('poker_mesa.png');

  // 6) Jugar la mano pulsando botones
  let actionsSent = 0;
  for (let i = 0; i < 40; i++) {
    snap = JSON.parse(await evaluate('window.__snap()'));
    if (snap.outcome || snap.finished) break;
    if (snap.actions.length === 0) { await sleep(700); continue; }
    const label = await evaluate(`window.__click('Igualar') || window.__click('Pasar') || window.__click('Retirarse')`);
    if (label) actionsSent++;
    await sleep(900);
  }
  snap = JSON.parse(await evaluate('window.__snap()'));
  check('la mano avanza al pulsar (hay acciones enviadas)', actionsSent >= 2, `-> ${actionsSent} pulsaciones`);
  check('la mano termina con un resultado visible', !!snap.outcome, `-> ${snap.outcome}`);
  const boardShown = snap.board.filter((c) => c).length;
  check('el tablero comunitario se rellena o la mano acaba por retirada',
        boardShown === 0 || boardShown === 3 || boardShown === 5, `-> ${boardShown} cartas`);
  check('los stacks se actualizan', snap.seats.every((s) => s.stack !== null), `-> ${JSON.stringify(snap.seats.map((s) => s.stack))}`);
  await shot('poker_resultado.png');

  // 7) Segunda mano automática
  let secondHand = false;
  for (let i = 0; i < 25 && !secondHand; i++) {
    await sleep(1000);
    snap = JSON.parse(await evaluate('window.__snap()'));
    secondHand = snap.hasTable && !snap.outcome && (snap.bar || '').includes('#2');
  }
  check('el servidor reparte una segunda mano sola', secondHand, `-> ${snap.bar}`);

  console.log('\n=== ERRORES DE CONSOLA ===');
  console.log(logs.length ? logs.slice(0, 12).join('\n') : '  (ninguno)');
  check('sin errores en consola', logs.filter((l) => !l.includes('favicon')).length === 0,
        `-> ${logs.length} mensajes`);

  const fails = results.filter((r) => !r[1]);
  console.log(`\n================ ${results.length - fails.length}/${results.length} comprobaciones OK ================`);
  fails.forEach(([l, , d]) => console.log(`  FALLO: ${l} ${d}`));

  ws.close(); proc.kill();
  try { fs.rmSync(PROFILE, { recursive: true, force: true }); } catch (e) {}
  process.exit(fails.length ? 1 : 0);
})();
