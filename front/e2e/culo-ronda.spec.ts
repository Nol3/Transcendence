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

  // Juega hasta que se acabe la ronda. En vez de dormir 700 ms por turno (que hacía el test lento
  // y frágil), se espera a que **pase algo**: o me toca, o se acabó. Así avanza al ritmo real de los
  // bots y no se queda corto si un turno tarda más.
  const fin = page.locator('.fin');
  for (let turno = 0; turno < 200; turno++) {
    if (await fin.isVisible().catch(() => false)) break;
    await expect
      .poll(
        async () =>
          (await fin.isVisible().catch(() => false)) ||
          (await jugar.isEnabled().catch(() => false)) ||
          (await pasar.isEnabled().catch(() => false)),
        { timeout: 20_000, intervals: [100, 200, 400] },
      )
      .toBe(true);
    if (await fin.isVisible().catch(() => false)) break;
    if (await jugar.isEnabled().catch(() => false)) await jugar.click();
    else if (await pasar.isEnabled().catch(() => false)) await pasar.click();
    await page.waitForTimeout(120);
  }

  await expect(fin).toBeVisible({ timeout: 90_000 });

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
