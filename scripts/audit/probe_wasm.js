// Verifica que el WASM recompilado arranca de verdad: Edge headless + CDP.
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

const PROFILE = path.join(os.tmpdir(), 'hermes_wasm_probe_' + Date.now());
const PORT = 9333;
const proc = spawn(BROWSER, [
  '--headless=new', '--disable-gpu', '--enable-unsafe-swiftshader',
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
    if (m.method === 'Runtime.consoleAPICalled') logs.push(`[console.${m.params.type}] ` + m.params.args.map((a) => a.value ?? a.description ?? '').join(' '));
    if (m.method === 'Runtime.exceptionThrown') logs.push('[exception] ' + (m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text));
  };
  const send = (method, params = {}) => new Promise((res) => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
  await new Promise((r) => (ws.onopen = r));

  await send('Runtime.enable'); await send('Log.enable'); await send('Page.enable');
  await send('Page.navigate', { url: URL_GAME });
  // Margen para wasm + assets + arranque del bucle. El .data son ~14 MB, así que en
  // frío (o por HTTPS) puede tardar: si se queda corto, el canvas aún está negro y no
  // aparecen las texturas de las cartas.
  const espera = Number(process.argv[3] || 12000);
  await sleep(espera);

  const probe = await send('Runtime.evaluate', {
    expression: "window.__probe ? window.__probe() : JSON.stringify({probe:'ausente'})",
    returnByValue: true,
  });
  const canvas = await send('Runtime.evaluate', {
    expression: "(()=>{const c=document.querySelector('canvas');if(!c)return 'sin canvas';const gl=c.getContext('webgl2')||c.getContext('webgl');return JSON.stringify({w:c.width,h:c.height,gl:!!gl,renderer:gl?gl.getParameter(gl.RENDERER):null});})()",
    returnByValue: true,
  });
  const glerr = await send('Runtime.evaluate', {
    expression: "(()=>{const c=document.querySelector('canvas');if(!c)return 'n/a';const gl=c.getContext('webgl2')||c.getContext('webgl');return gl?String(gl.getError()):'sin gl';})()",
    returnByValue: true,
  });

  // ¿El canvas dibuja algo o es un lienzo negro?
  const pixels = await send('Runtime.evaluate', {
    expression: `(()=>{const c=document.querySelector('canvas');if(!c)return 'sin canvas';
      const t=document.createElement('canvas');t.width=c.width;t.height=c.height;
      const x=t.getContext('2d');x.drawImage(c,0,0);
      const d=x.getImageData(0,0,t.width,t.height).data;
      let nonBlack=0,total=0,sum=0,white=0;
      for(let i=0;i<d.length;i+=4*53){total++;const l=(d[i]+d[i+1]+d[i+2])/3;sum+=l;
        if(l>18)nonBlack++; if(l>200)white++;}
      return JSON.stringify({muestras:total,pctNoNegro:Math.round(nonBlack/total*100),
        pctBlanco:Math.round(white/total*100),lumaMedia:Math.round(sum/total)});})()`,
    returnByValue: true,
  });

  const shot = await send('Page.captureScreenshot', { format: 'png' });
  if (shot.result && shot.result.data) {
    fs.writeFileSync(path.join(__dirname, 'juego_menu.png'), Buffer.from(shot.result.data, 'base64'));
  }

  console.log('\n=== PROBE (estado interno del juego) ===');
  console.log(probe.result?.result?.value);
  console.log('\n=== CANVAS/WebGL ===');
  console.log(canvas.result?.result?.value);
  console.log('glGetError:', glerr.result?.result?.value);
  console.log('\n=== PIXELES DEL CANVAS (¿dibuja o está negro?) ===');
  console.log(pixels.result?.result?.value);
  console.log('\n=== LOGS DEL NAVEGADOR (' + logs.length + ') ===');
  logs.slice(0, 40).forEach((l) => console.log('  ' + l));
  if (!logs.length) console.log('  (sin mensajes: ni errores ni warnings)');

  ws.close(); proc.kill();
  try { fs.rmSync(PROFILE, { recursive: true, force: true }); } catch (e) {}
  process.exit(0);
})();
