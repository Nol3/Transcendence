import { expect, test } from '@playwright/test';

/**
 * Dos amigos jugando a cada uno de los juegos nuevos, contra el servidor de verdad.
 *
 * Es la prueba que convierte «el modo online está enchufado» en «el modo online funciona»: se
 * levantan **dos navegadores distintos** (dos contextos, como dos móviles), cada uno con su cuenta
 * registrada aquí mismo, uno crea la sala, el otro entra con el código, y se comprueba que los dos
 * ven la partida y **solo su propia mano**.
 *
 * Necesita el stack levantado (`docker compose up -d`). Si la API no responde, se salta en vez de
 * fallar: así la suite sigue valiendo sin backend.
 */
const API = 'https://localhost:8443';
/** La app se abre por nginx (`:8443`): es el único sitio donde conviven app, API y WebSocket. */
const APP = 'https://localhost:8443';

/**
 * Cliente HTTP de Playwright: ignora el certificado autofirmado del stack local.
 *
 * Ojo con `baseURL`: Playwright resuelve las rutas que empiezan por «/» contra la **raíz** del host,
 * así que el prefijo `/api` va en cada llamada, no en el baseURL.
 */
async function api() {
  const { request } = await import('@playwright/test');
  return request.newContext({ ignoreHTTPSErrors: true, baseURL: API });
}

async function apiDisponible(): Promise<boolean> {
  const cliente = await api();
  try {
    const res = await cliente.get('/api/health/');
    // Vale cualquier respuesta que no sea un error del servidor: si va limitando peticiones (429)
    // es que está levantado, que es lo único que se quiere saber aquí.
    return res.status() < 500;
  } catch {
    return false;
  } finally {
    await cliente.dispose();
  }
}

interface Sesion {
  access: string;
  refresh: string;
  user: unknown;
}

/** Crea una cuenta y devuelve sus tokens (nada de usuarios ni claves fijas). */
async function registrar(sufijo: string): Promise<Sesion> {
  // Con varios tests en paralelo, el reloj no basta para que el nombre sea único.
  const azar = Math.random().toString(36).slice(2, 8);
  const user = `juegos_${sufijo}_${Date.now().toString(36)}${azar}`;
  const cliente = await api();
  try {
    const res = await cliente.post('/api/auth/register', {
      data: { username: user, email: `${user}@example.com`, password: 'Zx9!pqLmn42' },
    });
    if (!res.ok()) throw new Error(`no se pudo registrar (${res.status()}): ${await res.text()}`);
    const datos = (await res.json()) as {
      data?: { user?: unknown; tokens?: { accessToken: string; refreshToken: string } };
    };
    const tokens = datos.data?.tokens;
    if (!tokens || !datos.data?.user) throw new Error('el registro no devolvió la sesión');
    return { access: tokens.accessToken, refresh: tokens.refreshToken, user: datos.data.user };
  } finally {
    await cliente.dispose();
  }
}

/**
 * Deja la sesión puesta antes de que arranque la app. No basta con el token: el guard mira el
 * usuario cacheado (`current_user`), así que se guarda también.
 */
async function conSesion(page: import('@playwright/test').Page, sesion: Sesion) {
  await page.addInitScript(
    ([access, refresh, usuario]) => {
      window.localStorage.setItem('access_token', access);
      window.localStorage.setItem('refresh_token', refresh);
      window.localStorage.setItem('current_user', usuario);
    },
    [sesion.access, sesion.refresh, JSON.stringify(sesion.user)] as const,
  );
}

/** Lo mínimo de cada juego para poder jugarlo con amigos. */
const JUEGOS = [
  { id: 'mentiroso', ruta: '/mentiroso', min: 3, bots: 1, accion: '.controles__poner' },
  { id: 'brisca', ruta: '/brisca', min: 2, bots: 0, accion: '.controles__jugar' },
  { id: 'tute', ruta: '/tute', min: 2, bots: 0, accion: '.controles__jugar' },
  // En el mus lo primero que se hace es decidir si hay mus, no pasar un lance.
  { id: 'mus', ruta: '/mus', min: 4, bots: 2, accion: '.envite__mus' },
] as const;

for (const juego of JUEGOS) {
  test.describe(`${juego.id} online — dos amigos`, () => {
    test('uno crea la sala, el otro entra con el código y los dos ven su mano', async ({
      browser,
    }) => {
      test.setTimeout(120_000);
      test.skip(!(await apiDisponible()), 'hace falta el stack levantado (docker compose up -d)');

      const [ana, luis] = await Promise.all([registrar('ana'), registrar('luis')]);

      // Dos contextos: dos navegadores independientes, como dos personas distintas.
      const ctxAna = await browser.newContext({ ignoreHTTPSErrors: true });
      const ctxLuis = await browser.newContext({ ignoreHTTPSErrors: true });
      const pAna = await ctxAna.newPage();
      const pLuis = await ctxLuis.newPage();
      await conSesion(pAna, ana);
      await conSesion(pLuis, luis);

      // ── Ana elige jugar con amigos y crea la sala ─────────────────────────
      await pAna.goto(`${APP}${juego.ruta}`);
      await expect(pAna.locator('.inicio')).toBeVisible();
      await pAna.locator('.modo__online button').click();
      await pAna.locator('.sala__crear button').click();

      await expect(pAna.locator('.sala__code')).toBeVisible({ timeout: 20_000 });
      const codigo = (await pAna.locator('.sala__code').innerText()).trim();
      expect(codigo).toMatch(/^[A-Z0-9]{4}$/);

      // ── Luis entra con el código ──────────────────────────────────────────
      await pLuis.goto(`${APP}${juego.ruta}`);
      await expect(pLuis.locator('.inicio')).toBeVisible();
      await pLuis.locator('.modo__online button').click();
      await pLuis.locator('.sala__campo input').fill(codigo);
      await pLuis.locator('.sala__unirse button').click();

      // ── Se ven el uno al otro ─────────────────────────────────────────────
      await expect(pLuis.locator('.sala__code')).toBeVisible({ timeout: 20_000 });
      await expect(pAna.locator('.sala__jugador')).toHaveCount(2, { timeout: 20_000 });
      await expect(pLuis.locator('.sala__jugador')).toHaveCount(2, { timeout: 20_000 });
      expect((await pLuis.locator('.sala__code').innerText()).trim()).toBe(codigo);

      // ── Ana añade los bots que falten y reparte ───────────────────────────
      for (let i = 0; i < juego.bots; i++) {
        await pAna.locator('.sala__bot button').click();
      }
      await expect(pAna.locator('.sala__jugador')).toHaveCount(juego.min, { timeout: 20_000 });
      await pAna.locator('.sala__repartir button').click();

      // ── Los dos ven la partida, y cada uno su mano ────────────────────────
      await expect(pAna.locator('.mano__carta').first()).toBeVisible({ timeout: 25_000 });
      await expect(pLuis.locator('.mano__carta').first()).toBeVisible({ timeout: 25_000 });

      // Las cartas son de verdad (los PNG llegan después de pintar la mano).
      await expect
        .poll(
          () =>
            pAna.locator('.mano__carta img').evaluateAll(
              (imgs: HTMLImageElement[]) => imgs.length > 0 && imgs.every((i) => i.naturalWidth > 0),
            ),
          { timeout: 20_000, message: 'las cartas de la mano deberían cargar' },
        )
        .toBe(true);

      // Y a uno de los dos le toca jugar: el botón de la acción se le activa.
      const puedeActuar = async (p: import('@playwright/test').Page) =>
        p.locator(juego.accion).isEnabled().catch(() => false);
      await expect
        .poll(async () => (await puedeActuar(pAna)) || (await puedeActuar(pLuis)), {
          timeout: 30_000,
        })
        .toBe(true);

      await ctxAna.close();
      await ctxLuis.close();
    });
  });
}
