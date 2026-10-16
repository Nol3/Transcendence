import { expect, test } from '@playwright/test';

import { GAME_CATALOG } from '../src/app/core/games/game-catalog';
import {
  bootAuthenticated,
  mockAuthLogout,
  mockAuthMe,
  mockAuthRefresh,
  mockLeaderboard,
  setAuthToken,
  spaNavigate,
} from './helpers';

/**
 * Apartado «Juegos»: la parrilla que reúne todo lo jugable.
 *
 * Las comprobaciones van por selectores y por destinos (`href`), no por el texto, para
 * que no dependan del idioma en que se abra la app.
 */
test.describe('Apartado Juegos', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/**', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ count: 0, next: null, previous: null, results: [] }),
      }),
    );
    await setAuthToken(page);
    await mockAuthMe(page);
    await mockAuthRefresh(page);
    await mockAuthLogout(page);
    await mockLeaderboard(page);
    await bootAuthenticated(page);
  });

  test('necesita sesión', async ({ page }) => {
    // Sin token, el guard manda a iniciar sesión. Hay que limpiar el almacén *antes*
    // de que arranque la app y recargar de verdad: `spaNavigate` cambia la ruta sin
    // volver a cargar el documento, así que el script no llegaría a correr.
    await page.addInitScript(() => window.localStorage.clear());
    await page.goto('/games');
    await expect(page).toHaveURL(/\/login/);
  });

  test('lista los juegos con su nombre, modo y botón de jugar', async ({ page }) => {
    await spaNavigate(page, '/games');

    const tarjetas = page.locator('.game-card');
    // El catálogo manda: si se añade un juego, el test sigue solo.
    await expect(tarjetas).toHaveCount(GAME_CATALOG.length);

    // Cada tarjeta: nombre con texto, un distintivo de modo y etiquetas.
    for (const tarjeta of await tarjetas.all()) {
      await expect(tarjeta.locator('.game-card__name')).not.toBeEmpty();
      await expect(tarjeta.locator('app-badge')).not.toBeEmpty();
      expect(await tarjeta.locator('.game-card__tag').count()).toBeGreaterThan(0);
    }
  });

  test('el botón de cada juego abre su pantalla', async ({ page }) => {
    await spaNavigate(page, '/games');
    const tarjetas = page.locator('.game-card');
    await expect(tarjetas).toHaveCount(GAME_CATALOG.length);

    // El botón es un <button> con el enrutado dentro, así que la única forma honesta
    // de comprobar el destino es pulsarlo. El orden es el del catálogo.
    const destinos = GAME_CATALOG.map((g) => new RegExp(`${g.route}$`));
    for (let i = 0; i < destinos.length; i++) {
      await spaNavigate(page, '/games');
      await tarjetas.nth(i).locator('.game-card__pie button').click();
      await expect(page).toHaveURL(destinos[i]);
    }
  });
});
