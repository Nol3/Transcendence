const { chromium } = require('playwright');

(async () => {
  const url = process.argv[2] || 'https://localhost/game/';
  const consoleMsgs = [];
  const errors = [];
  const browser = await chromium.launch({
    headless: true,
    args: ['--use-gl=swiftshader', '--ignore-certificate-errors', '--no-sandbox'],
  });
  const ctx = await browser.newContext({ ignoreHTTPSErrors: true });
  const page = await ctx.newPage();
  page.on('console', (m) => consoleMsgs.push(`[${m.type()}] ${m.text()}`));
  page.on('pageerror', (e) => errors.push('PAGEERROR: ' + e.message));

  let status = 'n/a';
  try {
    const resp = await page.goto(url, { waitUntil: 'load', timeout: 45000 });
    status = resp ? resp.status() : 'no-response';
    await page.waitForSelector('canvas', { timeout: 20000 });
    // Give the WASM runtime + 14MB .data preload time to boot the game loop
    await page.waitForTimeout(8000);
  } catch (e) {
    errors.push('NAV: ' + e.message);
  }

  const info = await page
    .evaluate(() => {
      const c = document.querySelector('canvas');
      let gl = false;
      try {
        gl = !!(c && (c.getContext('webgl2') || c.getContext('webgl')));
      } catch (_) {}
      return {
        hasCanvas: !!c,
        canvasW: c ? c.width : 0,
        canvasH: c ? c.height : 0,
        title: document.title,
        hasModule: typeof window.Module !== 'undefined',
        crossOriginIsolated: window.crossOriginIsolated === true,
        webglReacquirable: gl,
      };
    })
    .catch((e) => ({ evalError: e.message }));

  await page.screenshot({ path: 'pw_game.png', fullPage: false }).catch(() => {});
  await browser.close();

  console.log('HTTP_STATUS=' + status);
  console.log('INFO=' + JSON.stringify(info));
  console.log('CONSOLE_ERRORS=' + consoleMsgs.filter((m) => m.startsWith('[error]')).length);
  consoleMsgs
    .filter((m) => m.startsWith('[error]'))
    .slice(0, 12)
    .forEach((m) => console.log('  ' + m));
  console.log('PAGE_ERRORS=' + errors.length);
  errors.slice(0, 8).forEach((e) => console.log('  ' + e));
})();
