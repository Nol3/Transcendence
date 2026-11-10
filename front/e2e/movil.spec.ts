import { expect, test } from '@playwright/test';
import {
  bootAuthenticated,
  mockAuthLogout,
  mockAuthMe,
  mockAuthRefresh,
  mockLeaderboard,
  spaNavigate,
} from './helpers';

/**
 * Lo que se comprueba aquí es lo que se rompe de verdad en un móvil: que nada se salga de ancho
 * (obliga a hacer scroll lateral en toda la página) y que se pueda jugar con el dedo.
 *
 * El tamaño lo pone el proyecto `movil` de `playwright.config.ts` (Pixel 7). Para lanzarlo:
 *   npx playwright test --project=movil
 */
test.describe('móvil @movil', () => {
  const SIN_DESBORDE = async (page: import('@playwright/test').Page) => {
    const desborde = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(desborde, 'la página se sale de ancho').toBeLessThanOrEqual(1);
  };

  test('la portada y el login caben en la pantalla @movil', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await SIN_DESBORDE(page);

    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    await SIN_DESBORDE(page);
  });

  test('las pantallas con sesión tampoco se salen @movil', async ({ page }) => {
    await mockAuthMe(page);
    await mockAuthRefresh(page);
    await mockAuthLogout(page);
    await mockLeaderboard(page);
    await bootAuthenticated(page);

    for (const ruta of ['/games', '/culo', '/profile', '/poker']) {
      await spaNavigate(page, ruta);
      await page.waitForTimeout(600);
      await SIN_DESBORDE(page);
    }
  });

  test('los botones se pueden tocar con el dedo @movil', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');

    // WCAG 2.2 AA (2.5.8): 24×24 como mínimo. Aquí se exige eso, no los 44 de Apple, para no
    // convertir esto en un test de diseño.
    const pequenos = await page.evaluate(() =>
      [...document.querySelectorAll('button, [role="button"]')]
        .map((b) => {
          const c = b.getBoundingClientRect();
          return {
            texto: (b.getAttribute('aria-label') || b.textContent || '').trim().slice(0, 24),
            ancho: Math.round(c.width),
            alto: Math.round(c.height),
          };
        })
        .filter((b) => b.ancho > 0 && b.alto > 0 && (b.ancho < 24 || b.alto < 24)),
    );

    expect(pequenos, `botones por debajo de 24px: ${JSON.stringify(pequenos)}`).toEqual([]);
  });

  test('la mesa del Culo se juega con el dedo @movil', async ({ page }) => {
    // El reparto y los turnos de los bots van con animación y esperas: 30 s se queda corto.
    test.setTimeout(90_000);
    await mockAuthMe(page);
    await mockAuthRefresh(page);
    await mockAuthLogout(page);
    await mockLeaderboard(page);
    await bootAuthenticated(page);
    await spaNavigate(page, '/culo');

    await page.locator('.modo__local button').first().click();
    await expect(page.locator('.mesa')).toBeVisible();

    // Espera a que sea mi turno. No vale esperar a «Pasar»: en el Culo puede tocarte con «Pasar»
    // deshabilitado (si estás obligado a jugar), así que se espera a que se active **cualquiera**
    // de los dos botones.
    const jugar = page.locator('.controles__botones button').first();
    const pasar = page.locator('.controles__botones button').nth(1);
    await expect
      .poll(async () => (await jugar.isEnabled()) || (await pasar.isEnabled()), { timeout: 30000 })
      .toBe(true);

    // La mano tiene que caber entera: con 10 cartas y 64 px fijos se salía por la izquierda y
    // quedaba media mano fuera de la pantalla.
    const cartas = page.locator('.mano__carta');
    const cuantas = await cartas.count();
    expect(cuantas, 'debería haber cartas en la mano').toBeGreaterThan(0);

    for (let i = 0; i < cuantas; i++) {
      const caja = (await cartas.nth(i).boundingBox())!;
      expect(caja.y, `la carta ${i} se sale por arriba`).toBeGreaterThanOrEqual(0);
      // La rotación del abanico ensancha la caja: se deja un margen de una carta.
      expect(caja.x, `la carta ${i} se sale por la izquierda`).toBeGreaterThan(-20);
      expect(caja.x + caja.width, `la carta ${i} se sale por la derecha`).toBeLessThanOrEqual(390 + 40);
      // Y el borde inferior, pegado al de la pantalla.
      expect(caja.y + caja.height, `la carta ${i} se sale por abajo`).toBeLessThanOrEqual(844);
    }

    const antes = await cartas.count();
    const boton = (await jugar.isEnabled()) ? jugar : pasar;
    const cajaBoton = (await boton.boundingBox())!;
    // F4: los botones de la mesa van a 56 px de alto, a lo ancho, en la zona del pulgar.
    expect(cajaBoton.height, 'el botón debería medir al menos 56 px de alto').toBeGreaterThanOrEqual(56);
    expect(cajaBoton.width, 'el botón debería ocupar el ancho disponible').toBeGreaterThan(120);
    // Toque de verdad (no `click` de ratón) en el centro del botón.
    await page.touchscreen.tap(cajaBoton.x + cajaBoton.width / 2, cajaBoton.y + cajaBoton.height / 2);

    await expect
      .poll(
        async () => {
          const enMesa = await page.locator('.jugada__cartas app-playing-card').count();
          const enMano = await page.locator('.mano__carta').count();
          return enMesa > 0 || enMano < antes;
        },
        { timeout: 15000 },
      )
      .toBe(true);
  });
});
