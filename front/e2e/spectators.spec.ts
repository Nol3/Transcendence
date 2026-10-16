import { test, expect } from '@playwright/test';
import {
  bootAuthenticated,
  mockAuthMe,
  mockAuthLogout,
  mockAuthRefresh,
  mockLeaderboard,
  setAuthToken,
  spaNavigate,
} from './helpers';

/**
 * Espectadores: entrada desde el lobby y modo de solo lectura (5.4).
 *
 * Ojo: el WebSocket de la mesa **no** se simula aquí — `page.routeWebSocket` no
 * intercepta en este entorno (comprobado: el handler nunca se llamaba), así que
 * lo que se cubre es la parte REST y de navegación: la lista de mesas en vivo y
 * que «Ver» deja la página en modo espectador (sin ofrecer buscar partida, porque
 * ya está dentro de una mesa).
 *
 * La verificación real del modo espectador —sin asiento, sin cartas ajenas, sin
 * poder actuar y con chat de mesa— está en `scripts/audit/probe_spectators.py`,
 * que habla con el servidor de verdad (12/12).
 */
test.describe('Espectadores — lobby y entrada', () => {
  test.beforeEach(async ({ page }) => {
    await setAuthToken(page);
    await mockAuthMe(page);
    await mockAuthRefresh(page);
    await mockAuthLogout(page);
    await mockLeaderboard(page);

    // Mesas en vivo: se mockean para que el test no dependa de las mesas que haya
    // abiertas de verdad en el proceso (el registro vive en memoria).
    await page.route('**/poker/tables/', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          count: 2,
          results: [
            {
              table_id: 'viva01', seats: 2, players: ['ana', 'Bot Nol3'],
              small_blind: 5, big_blind: 10, hand_number: 7, finished: false,
              tournament_id: null,
            },
            {
              table_id: 'fin02', seats: 3, players: ['a', 'b', 'c'],
              small_blind: 1, big_blind: 2, hand_number: 12, finished: true,
              tournament_id: null,
            },
          ],
        }),
      }),
    );

    await bootAuthenticated(page);
  });

  test('el lobby lista las mesas en vivo, con las terminadas marcadas', async ({ page }) => {
    await spaNavigate(page, '/poker');
    await expect(page.locator('.live__item')).toHaveCount(2, { timeout: 5000 });

    const primera = page.locator('.live__item').first();
    await expect(primera).toContainText('ana');
    await expect(primera).toContainText('7');
    await expect(primera).toContainText('LIVE');

    await expect(page.locator('.live__item').nth(1)).toContainText('FINISHED');
  });

  test('«Ver» lleva a la mesa en modo espectador', async ({ page }) => {
    await spaNavigate(page, '/poker');
    await expect(page.locator('.live__item')).toHaveCount(2, { timeout: 5000 });

    await page.locator('.live__item').first().getByRole('button', { name: /watch/i }).click();

    // La URL queda con la mesa (compartible)…
    await expect(page).toHaveURL(/\/poker\?table=viva01/, { timeout: 5000 });
    // …y ya no se ofrece buscar partida: la página está dentro de una mesa.
    await expect(page.getByRole('button', { name: /find a match/i })).toHaveCount(0);
  });
});
