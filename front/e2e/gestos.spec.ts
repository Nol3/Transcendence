import { expect, test } from '@playwright/test';
import { bootAuthenticated, mockAuthLogout, mockAuthMe, mockAuthRefresh, mockLeaderboard, spaNavigate } from './helpers';

/** Arranca una mesa del Culo contra bots y espera a que sea mi turno. */
async function miTurno(page: import('@playwright/test').Page) {
  await mockAuthMe(page);
  await mockAuthRefresh(page);
  await mockAuthLogout(page);
  await mockLeaderboard(page);
  await bootAuthenticated(page);
  await spaNavigate(page, '/culo');
  await page.locator('.modo__local button').first().click();
  const jugar = page.locator('.controles__botones button').first();
  const pasar = page.locator('.controles__botones button').nth(1);
  await expect
    .poll(async () => (await jugar.isEnabled()) || (await pasar.isEnabled()), { timeout: 30_000 })
    .toBe(true);
  return { jugar, pasar };
}

test.describe('Gestos de la mano', () => {
  test('el toque mantenido enseña la carta y se cierra al tocar', async ({ page }) => {
    test.setTimeout(90_000);
    await miTurno(page);

    const caja = (await page.locator('.mano__carta').first().boundingBox())!;
    const x = caja.x + caja.width / 2;
    const y = caja.y + caja.height / 2;

    await page.mouse.move(x, y);
    await page.mouse.down();
    await page.waitForTimeout(700);
    await expect(page.locator('.vista')).toBeVisible();
    await page.mouse.up();

    // Un toque en cualquier sitio la cierra.
    await page.mouse.click(8, 8);
    await expect(page.locator('.vista')).toHaveCount(0);
  });

  test('el doble toque juega la carta sin pasar por el botón', async ({ page }) => {
    test.setTimeout(90_000);
    const { jugar } = await miTurno(page);

    // Se busca una carta que de verdad se pueda jugar (en el Culo no todas valen).
    const mano = page.locator('.mano__carta:not([disabled])');
    const cuantas = await mano.count();
    let jugable = -1;
    for (let i = 0; i < cuantas; i++) {
      await mano.nth(i).click({ force: true });
      await page.waitForTimeout(150);
      if (await jugar.isEnabled()) {
        jugable = i;
        break;
      }
    }
    expect(jugable, 'debería haber alguna carta jugable').toBeGreaterThanOrEqual(0);

    // Se deja pasar el margen del doble toque para que el `dblclick` cuente desde cero.
    await page.waitForTimeout(400);
    const antes = await mano.count();

    // Los bots juegan entre medias y la mano se recoloca: se reintenta el gesto hasta tres veces
    // antes de darlo por fallido (si no, el test falla por una carrera con el turno, no por el gesto).
    for (let intento = 0; intento < 3; intento++) {
      await mano.nth(jugable).dblclick({ force: true });
      const cambio = await expect
        .poll(async () => mano.count(), { timeout: 4_000 })
        .not.toBe(antes)
        .then(() => true)
        .catch(() => false);
      if (cambio) return;
      await page.waitForTimeout(300);
    }
    expect(await mano.count(), 'el doble toque debería jugar la carta').not.toBe(antes);
  });
});
