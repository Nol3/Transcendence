import { expect, test } from '@playwright/test';

/**
 * Dos amigos jugando en la misma sala, contra el servidor de verdad.
 *
 * Es la prueba de lo que pidió el usuario: que el Culo se juegue entre personas. Se
 * levantan **dos navegadores distintos** (dos contextos, como dos móviles), cada uno con
 * su cuenta —registrada aquí mismo, sin tocar credenciales de nadie—, uno crea la sala,
 * el otro entra con el código, y se comprueba que los dos ven la partida y **solo su
 * propia mano**.
 *
 * Necesita el stack levantado (`docker compose up -d`). Si la API no responde, se salta
 * en vez de fallar: así la suite sigue valiendo sin backend.
 */
const API = 'https://localhost:8443';
/**
 * La app se abre por nginx (`:8443`), no por el contenedor del front (`:4200`): es el
 * único sitio donde conviven la app, la API y el WebSocket, que es como la usa la gente.
 */
const APP = 'https://localhost:8443';

/**
 * Cliente HTTP de Playwright: ignora el certificado autofirmado del stack local.
 *
 * Ojo con `baseURL`: Playwright resuelve las rutas que empiezan por «/» contra la **raíz**
 * del host, así que el prefijo `/api` va en cada llamada, no en el baseURL.
 */
async function api() {
  const { request } = await import('@playwright/test');
  return request.newContext({ ignoreHTTPSErrors: true, baseURL: API });
}

async function apiDisponible(): Promise<boolean> {
  const cliente = await api();
  try {
    const res = await cliente.get('/api/health/');
    return res.ok();
  } catch {
    return false;
  } finally {
    await cliente.dispose();
  }
}

/** Crea una cuenta y devuelve sus tokens (nada de usuarios ni claves fijas). */
interface Sesion {
  access: string;
  refresh: string;
  user: unknown;
}

async function registrar(sufijo: string): Promise<Sesion> {
  const user = `culo_${sufijo}_${Date.now().toString(36)}`; // usuario nuevo cada vez
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
    return {
      access: tokens.accessToken,
      refresh: tokens.refreshToken,
      user: datos.data.user,
    };
  } finally {
    await cliente.dispose();
  }
}

/**
 * Deja la sesión puesta antes de que arranque la app. No basta con el token: el guard
 * mira el usuario cacheado (`current_user`), así que se guarda también.
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

test.describe('Culo online — dos amigos', () => {
  test('uno crea la sala, el otro entra con el código y juegan', async ({ browser }) => {
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

    // ── Ana crea la sala ────────────────────────────────────────────────────
    await pAna.goto(`${APP}/culo`);
    await expect(pAna.locator('.inicio')).toBeVisible();
    await pAna.locator('.modo').nth(1).locator('button').click(); // «Crear sala»

    await expect(pAna.locator('.lobby')).toBeVisible({ timeout: 15_000 });
    const codigo = (await pAna.locator('.lobby__code').innerText()).trim();
    expect(codigo).toMatch(/^[A-Z0-9]{4}$/);

    // ── Luis entra con el código ────────────────────────────────────────────
    await pLuis.goto(`${APP}/culo`);
    await expect(pLuis.locator('.inicio')).toBeVisible();
    await pLuis.locator('.modo__codigo input').fill(codigo);
    await pLuis.locator('.modo').nth(2).locator('button').click(); // «Entrar»

    // ── Se ven el uno al otro ───────────────────────────────────────────────
    await expect(pLuis.locator('.lobby')).toBeVisible({ timeout: 15_000 });
    await expect(pAna.locator('.lobby__jugador')).toHaveCount(2, { timeout: 15_000 });
    await expect(pLuis.locator('.lobby__jugador')).toHaveCount(2, { timeout: 15_000 });

    // El código es el mismo para los dos (están en la misma sala).
    expect((await pLuis.locator('.lobby__code').innerText()).trim()).toBe(codigo);

    // ── Ana mete un bot y reparte ───────────────────────────────────────────
    // El Culo pide tres jugadores como mínimo: dos amigos y un bot hacen mesa.
    await pAna.getByRole('button', { name: /bot/i }).click();
    await expect(pAna.locator('.lobby__jugador')).toHaveCount(3, { timeout: 10_000 });
    await pAna.locator('.lobby__repartir button').click();

    await expect(pAna.locator('.mesa')).toBeVisible({ timeout: 15_000 });
    await expect(pLuis.locator('.mesa')).toBeVisible({ timeout: 15_000 });

    // Cada uno ve su mano, y los dos ven al rival con cartas (pero sin verlas).
    const manoAna = await pAna.locator('.mano__carta').count();
    const manoLuis = await pLuis.locator('.mano__carta').count();
    expect(manoAna).toBeGreaterThan(0);
    expect(manoLuis).toBeGreaterThan(0);
    // Tres en la mesa (dos amigos y un bot): cada uno ve a los otros dos.
    await expect(pAna.locator('.rival')).toHaveCount(2);
    await expect(pLuis.locator('.rival')).toHaveCount(2);

    // ── Luis recarga la página a mitad de partida ───────────────────────────
    // En el móvil el navegador recarga solo al volver del segundo plano. El código queda
    // en la URL, así que vuelve a **su** mesa y a **su** mano, sin pasar por el menú, y
    // sin que la conexión vieja lo eche de la sala.
    await pLuis.reload();
    await expect(pLuis.locator('.mesa')).toBeVisible({ timeout: 20_000 });
    await expect(pLuis.locator('.rival')).toHaveCount(2);
    await expect
      .poll(() => pLuis.locator('.mano__carta').count(), { timeout: 15_000 })
      .toBeGreaterThan(0);

    // Las cartas son las de la baraja española y cargan de verdad (los PNG llegan después
    // de pintar la mano, así que se espera a que estén todas).
    await expect
      .poll(
        () =>
          pAna.locator('.mano__carta img').evaluateAll(
            (imgs: HTMLImageElement[]) => imgs.length > 0 && imgs.every((i) => i.naturalWidth > 0),
          ),
        { timeout: 15_000, message: 'las cartas de la mano deberían cargar' },
      )
      .toBe(true);

    // Y quien tiene el turno puede actuar (los botones se activan para uno de los dos).
    const activo = async (p: import('@playwright/test').Page) =>
      p.locator('.controles__botones button').nth(1).isEnabled().catch(() => false);
    await expect
      .poll(async () => (await activo(pAna)) || (await activo(pLuis)), { timeout: 20_000 })
      .toBe(true);

    await ctxAna.close();
    await ctxLuis.close();
  });
});
