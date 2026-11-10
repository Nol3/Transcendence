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
 * La movilidad de la carta: se inclina hacia el puntero y vuelve a plana al salir.
 *
 * Se comprueba sobre la mesa real del Culo (la mano ya repartida), no sobre un banco de pruebas: lo
 * que importa es que funcione dentro del botón de la mano, que es donde vive en los cinco juegos.
 */
test.describe('movilidad de las cartas', () => {
  const abrirMano = async (page: import('@playwright/test').Page) => {
    await mockAuthMe(page);
    await mockAuthRefresh(page);
    await mockAuthLogout(page);
    await mockLeaderboard(page);
    await bootAuthenticated(page);
    await spaNavigate(page, '/culo');
    await page.locator('.modo__local button').first().click();
    await expect(page.locator('.mesa')).toBeVisible();
  };

  test('la carta se inclina hacia el puntero y vuelve a plana', async ({ page }) => {
    await abrirMano(page);

    const carta = page.locator('.mano__carta .pc').first();
    await expect(carta).toBeVisible();

    // En el centro, plana.
    await carta.hover();
    await page.waitForTimeout(250);
    const centrada = await carta.evaluate((el) => getComputedStyle(el).transform);

    // En una esquina, inclinada: el transform cambia y la variable tiene grados de verdad.
    await carta.hover({ position: { x: 4, y: 4 } });
    await page.waitForTimeout(250);
    const inclinada = await carta.evaluate((el) => getComputedStyle(el).transform);
    expect(inclinada).not.toBe(centrada);

    const giroY = await carta.evaluate((el) =>
      Number.parseFloat(getComputedStyle(el).getPropertyValue('--pc-ry')),
    );
    const giroX = await carta.evaluate((el) =>
      Number.parseFloat(getComputedStyle(el).getPropertyValue('--pc-rx')),
    );
    expect(Math.abs(giroY), 'debería girar en el eje Y').toBeGreaterThan(1);
    expect(Math.abs(giroX), 'debería girar en el eje X').toBeGreaterThan(1);
    // Pero contenido: el tope son 7° (con dedo, 4).
    expect(Math.abs(giroY)).toBeLessThanOrEqual(7.01);

    // Al salir, vuelve al centro.
    await page.mouse.move(0, 0);
    await page.waitForTimeout(300);
    const fuera = await carta.evaluate((el) =>
      Number.parseFloat(getComputedStyle(el).getPropertyValue('--pc-ry')),
    );
    expect(Math.abs(fuera)).toBeLessThan(0.01);
  });

  test.describe('con movimiento reducido', () => {
    test.use({ reducedMotion: 'reduce' });

    test('no se inclina ni brilla', async ({ page }) => {
      await abrirMano(page);

      const carta = page.locator('.mano__carta .pc').first();
      await expect(carta).toBeVisible();
      await carta.hover({ position: { x: 4, y: 4 } });
      await page.waitForTimeout(250);

      const giro = await carta.evaluate((el) => getComputedStyle(el).getPropertyValue('--pc-ry').trim());
      expect(giro === '' || giro === '0deg').toBe(true);

      // Y el brillo está apagado.
      const brillo = await carta.evaluate(
        (el) => getComputedStyle(el, '::after').display,
      );
      expect(brillo).toBe('none');
    });
  });
});
