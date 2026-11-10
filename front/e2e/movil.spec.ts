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

    // Con el abanico, el centro de la carta puede quedar tapado por la siguiente (o por la
    // cabecera si Playwright la sube al borde). Se pulsa la esquina que se ve, como haría un dedo.
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));

    // Se toca la **última** carta: en el abanico cada carta tapa el borde derecho de la anterior,
    // así que el único trozo que siempre se ve es el derecho de la última. Con el centro de una
    // carta cualquiera, el dedo cae en la vecina.
    const carta = page.locator('.mano__carta:not([disabled])').last();
    const caja = await carta.boundingBox();
    await carta.tap({
      position: { x: (caja?.width ?? 64) - 10, y: (caja?.height ?? 88) / 2 },
    });
    await expect(carta).toHaveAttribute('aria-pressed', 'true');

    const antes = await page.locator('.mano__carta').count();
    const boton = (await jugar.isEnabled()) ? jugar : pasar;
    await boton.tap();

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
