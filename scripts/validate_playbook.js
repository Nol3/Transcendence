#!/usr/bin/env node
/**
 * Playbook: login -> navigate to game-wrap -> verify iframe embeds game
 * Works with: Windows (PowerShell) or Linux (WSL)
 * Requires Node.js >= 18
 */

const BACKEND = process.env.BACKEND_URL || 'http://localhost:8000';
const FRONTEND = process.env.FRONTEND_URL || 'http://localhost:4200';
const STATIC_GAME = process.env.STATIC_GAME_URL || 'http://localhost:8000/static/game';

async function fetchJSON(url, opts = {}) {
  const res = await fetch(url, opts);
  let json = null;
  try { json = await res.json(); } catch {}
  return { ok: res.ok, status: res.status, json };
}

async function fetchHead(url) {
  try {
    const res = await fetch(url, { method: 'HEAD' });
    return { ok: res.ok, status: res.status, headers: Object.fromEntries(res.headers.entries()) };
  } catch (e) {
    return { ok: false, status: 0, headers: {} };
  }
}

const log = {
  ok: (s)=>console.log('[PASS] '+s),
  fail: (s)=>console.log('[FAIL] '+s),
  info: (s)=>console.log('[INFO] '+s),
};

async function waitFor(url, attempts=5, delayMs=2000){
  for(let i=0;i<attempts;i++){
    try {
      const res = await fetch(url);
      if (res.ok) return true;
    } catch(e) { /* ignore */ }
    await new Promise(r=>setTimeout(r, delayMs));
  }
  return false;
}

async function main(){
  console.log('[PLAYBOOK] Validating MVP login -> go to game-wrap -> iframe load');

  // 1) Health (wait for server to be ready)
  const healthy = await waitFor(`${BACKEND}/api/health/`, 10, 1000);
  if (healthy) {
    let r = await fetchJSON(`${BACKEND}/api/health/`);
    if (r.ok) log.ok(`Backend health OK ${r.status}`); else log.fail(`Backend health failed ${r?.status ?? ''}`);
  } else {
    log.fail('Backend health check could not reach server');
  }

  // 2) Login admin (admin123)
  r = await fetchJSON(`${BACKEND}/api/auth/login/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'admin', password: 'admin123' })
  });
  if (r.ok && r.json?.data) log.ok('Admin login succeeded'); else log.fail('Admin login failed');

  // 3) Frontend game-wrap page (wait for frontend to boot)
  const frontOk = await waitFor(`${FRONTEND}/game-wrap`, 20, 500);
  const front = await fetch(FRONTEND + '/game-wrap');
  if (front.ok) {
    const text = await front.text();
    const m = text.match(/<iframe[^>]+src=["']([^"']+)["']/i);
    const iframeSrc = m ? m[1] : null;
    if (iframeSrc) {
      log.info(`Iframe src detected: ${iframeSrc}`);
      const iframeURL = iframeSrc.startsWith('http') ? iframeSrc : new URL(iframeSrc, FRONTEND).toString();
      const head = await fetchHead(iframeURL);
      if (head.ok) log.ok(`Iframe URL accessible: ${iframeURL} (HEAD ${head.status})`);
      else log.fail(`Iframe URL not accessible: ${iframeURL} (HEAD ${head.status})`);
    } else {
      log.fail('No iframe src found on game-wrap page');
    }
  } else {
    log.fail(`Failed to load game-wrap page: ${FRONTEND} (${front.status})`);
  }

  // 4) WASM assets
  const assets = ['index.html','index.js','index.wasm','index.data'];
  for (const a of assets){
    const url = `${STATIC_GAME}/${a}`;
    const head = await fetchHead(url);
    if (head.ok) log.ok(`Asset available: ${url}`); else log.fail(`Missing asset: ${url}`);
  }
}

main().catch(e => { console.error('[ERROR]', e); process.exit(2); })
