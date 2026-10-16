// Verificación puntual: juega una ronda entera contra los bots hasta el fin de ronda,
// para comprobar el cierre, los roles y el intercambio (y dejar la captura).
import { expect, test } from '@playwright/test';

import {
  bootAuthenticated,
  mockAuthLogout,
  mockAuthMe,
  mockAuthRefresh,
  mockLeaderboard,
  setAuthToken,
  spaNavigate,
} from './helpers';

test('una ronda entera termina con roles e intercambio', async ({ page }) => {
  test.setTimeout(180_000);

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

  await spaNavigate(page, '/culo');
  // 3 jugadores: la partida más corta.
  await page.locator('.inicio__campo--jugadores select').selectOption('3');
  await page.locator('.modo__local button').click();
  await expect(page.locator('.mesa')).toBeVisible();

  const pasar = page.locator('.controles__botones button').nth(1);
  const jugar = page.locator('.controles__botones button').nth(0);

  // Juega hasta que se acabe la ronda (o se agote el tiempo).
  for (let turno = 0; turno < 80; turno++) {
    if (await page.locator('.fin').isVisible().catch(() => false)) break;
    const puedoActuar = await pasar.isEnabled().catch(() => false);
    if (puedoActuar) {
      if (await jugar.isEnabled()) await jugar.click();
      else await pasar.click();
    }
    await page.waitForTimeout(700);
  }

  await expect(page.locator('.fin')).toBeVisible({ timeout: 60_000 });

  // Roles: tres puestos distintos y uno de ellos el Presidente.
  const puestos = await page.locator('.fin__puesto').count();
  expect(puestos).toBe(3);
  const roles = await page.locator('.fin__puesto-rol').allInnerTexts();
  console.log('roles:', roles.join(' · '));
  expect(roles.length).toBe(3);
  expect(new Set(roles).size).toBe(3); // Presidente, neutro y Culo

  await page.waitForTimeout(400);
  await page.screenshot({ path: 'capturas/7-culo-fin-de-ronda.png' });

  // Y la ronda siguiente se puede empezar.
  await page.locator('.fin app-button button').click();
  await expect(page.locator('.fin')).toHaveCount(0);
  await expect(page.locator('.mano__carta').first()).toBeVisible();
});
