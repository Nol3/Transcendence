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
 * Match de torneo en una mesa de póker real (5.1).
 *
 * Al llegar desde el bracket con `?tournament=..&match=..`, la página pide al
 * backend la mesa del match y entra directo: sin cola y sin bots. Aquí se mockea
 * esa respuesta (el WebSocket no hace falta: lo que se comprueba es la pantalla
 * previa, que es la que decide si hay cola o partida de torneo).
 */
test.describe('Póker — match de torneo', () => {
  test.beforeEach(async ({ page }) => {
    await setAuthToken(page);
    await mockAuthMe(page);
    await mockAuthRefresh(page);
    await mockAuthLogout(page);
    await mockLeaderboard(page);
    await page.route('**/tournament/*/matches/*/table/', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          table_id: 'abc123',
          ws_path: '/ws/poker/table/abc123',
          opponent: { id: 2, username: 'rival' },
          small_blind: 5,
          big_blind: 10,
          starting_stack: 1000,
          tournament: { id: 1, name: 'E2E Cup' },
          match_id: 10,
        }),
      }),
    );
    await bootAuthenticated(page);
  });

  test('entra directo a la mesa del match, sin cola', async ({ page }) => {
    await spaNavigate(page, '/poker?tournament=1&match=10');
    await expect(page).toHaveURL(/\/poker\?tournament=1&match=10/, { timeout: 5000 });

    // El panel de torneo sustituye a la cola de espera.
    await expect(page.getByText('TOURNAMENT MATCH')).toBeVisible({ timeout: 5000 });
    await expect(page.getByText(/rival/).first()).toBeVisible();
    await expect(page.getByRole('button', { name: /find a match/i })).toHaveCount(0);
    await expect(page.getByText(/TOURNAMENTS|E2E Cup/).first()).toBeVisible();
  });

  test('sin parámetros de torneo sí aparece la cola', async ({ page }) => {
    await spaNavigate(page, '/poker');
    await expect(page.getByRole('button', { name: /find a match/i })).toBeVisible({
      timeout: 5000,
    });
    await expect(page.getByText('TOURNAMENT MATCH')).toHaveCount(0);
  });
});
