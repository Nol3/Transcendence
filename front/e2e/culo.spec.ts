import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

import {
  bootAuthenticated,
  mockAuthLogout,
  mockAuthMe,
  mockAuthRefresh,
  mockLeaderboard,
  quitarCspDeLosDocumentos,
  setAuthToken,
  spaNavigate,
} from './helpers';

/**
 * Culo (Presidente).
 *
 * La partida se juega de verdad: se reparte, los bots van moviendo solos y se comprueba
 * que la mesa responde. Los selectores van por clase y por estado (cartas, botones
 * habilitados), no por texto, para que no dependan del idioma.
 */
test.describe('Culo', () => {
  test.beforeEach(async ({ page }) => {
    // axe se inyecta como script y la CSP lo bloquearía (ver el helper).
    await quitarCspDeLosDocumentos(page);
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

  test('se explica antes de jugar y reparte una mesa', async ({ page }) => {
    await spaNavigate(page, '/culo');

    // Pantalla de ajustes con su explicación y el número de jugadores.
    await expect(page.locator('.inicio')).toBeVisible();
    await expect(page.locator('.inicio__campo select')).toHaveCount(2);

    // Las reglas se pueden leer antes de empezar.
    await page.locator('.culo__acciones button').first().click();
    await expect(page.locator('.reglas')).toBeVisible();
    expect(await page.locator('.reglas__cuerpo section').count()).toBeGreaterThan(4);
    await page.locator('.reglas__cerrar').click();
    await expect(page.locator('.reglas')).toHaveCount(0);

    // Repartir: aparece la mesa con rivales y mi mano.
    await page.locator('.modo__local button').click();
    await expect(page.locator('.mesa')).toBeVisible();
    await expect(page.locator('.rival')).toHaveCount(3); // 4 jugadores por defecto, 3 bots
    expect(await page.locator('.mano__carta').count()).toBeGreaterThan(0);

    // Las cartas son las de la baraja española y cargan de verdad.
    const src = await page.locator('.mano__carta app-playing-card img').first().getAttribute('src');
    // Ruta relativa a propósito (el <base href> de la app), así que sin barra inicial.
    expect(src).toContain('cards/es/');
    const cargadas = await page.locator('.mano__carta img').evaluateAll(
      (imgs: HTMLImageElement[]) => imgs.length > 0 && imgs.every((i) => i.naturalWidth > 0),
    );
    expect(cargadas).toBe(true);
  });

  test('se juega un turno contra los bots', async ({ page }) => {
    await spaNavigate(page, '/culo');
    await page.locator('.modo__local button').click();
    await expect(page.locator('.mesa')).toBeVisible();

    // Los bots juegan solos; se espera a que llegue mi turno (los botones se activan).
    const pasar = page.locator('.controles__botones button').nth(1);
    await expect(pasar).toBeEnabled({ timeout: 30000 });

    // Y se juega: la mesa o mi mano tienen que cambiar.
    const antes = await page.locator('.mano__carta').count();
    const jugar = page.locator('.controles__botones button').nth(0);
    if (await jugar.isEnabled()) {
      await jugar.click();
    } else {
      await pasar.click();
    }

    // Algo ha pasado: o hay jugada en la mesa, o tengo menos cartas, o hay registro.
    await expect
      .poll(async () => {
        const enMesa = await page.locator('.jugada__cartas app-playing-card').count();
        const enMano = await page.locator('.mano__carta').count();
        const lineas = await page.locator('.registro__linea').count();
        return enMesa + lineas + (antes - enMano);
      }, { timeout: 15000 })
      .toBeGreaterThan(0);
  });

  test('el diálogo de reglas maneja el foco como un modal', async ({ page }) => {
    await spaNavigate(page, '/culo');
    await page.locator('.modo__local button').click();
    await expect(page.locator('.mesa')).toBeVisible();

    // Se abre con el teclado, como haría quien no usa el ratón.
    const abrir = page.locator('.culo__btn').first();
    await abrir.focus();
    await abrir.press('Enter');
    await expect(page.locator('.reglas')).toBeVisible();

    const dentroDelDialogo = () =>
      page.evaluate(() => !!document.activeElement?.closest('.reglas'));

    // 1) Al abrirse, el foco entra en el diálogo (antes se quedaba en el botón de detrás,
    //    así que el primer tabulador se iba a la página de fondo).
    expect(await dentroDelDialogo()).toBe(true);

    // 2) El tabulador no se escapa: da la vuelta dentro.
    for (let i = 0; i < 6; i++) {
      await page.keyboard.press('Tab');
      expect(await dentroDelDialogo()).toBe(true);
    }
    await page.keyboard.press('Shift+Tab');
    expect(await dentroDelDialogo()).toBe(true);

    // 3) Al cerrarse, el foco vuelve a donde estaba.
    await page.locator('.reglas__cerrar').click();
    await expect(page.locator('.reglas')).toHaveCount(0);
    expect(
      await page.evaluate(() => document.activeElement?.classList.contains('culo__btn')),
    ).toBe(true);
  });

  test('la mesa no tiene violaciones graves de accesibilidad', async ({ page }) => {
    await spaNavigate(page, '/culo');
    await page.locator('.modo__local button').click();
    await expect(page.locator('.mesa')).toBeVisible();
    // Hay que dejar que acabe la animación de entrada: a mitad, el texto está a media
    // opacidad y axe lo mide como si tuviera mal contraste (falso positivo).
    await page.waitForTimeout(800);

    const informe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
    for (const v of informe.violations) {
      for (const nodo of v.nodes.slice(0, 4)) {
        const d = nodo.any?.[0]?.data ?? {};
        console.log(`  · ${v.id} [${v.impact}] ${nodo.target.join(' ')} → ${d.contrastRatio ?? ''} ${d.fgColor ?? ''} / ${d.bgColor ?? ''} :: ${(nodo.html ?? '').slice(0, 140)}`);
      }
    }
    const graves = informe.violations
      .filter((v) => v.impact === 'critical' || v.impact === 'serious')
      .map((v) => `${v.id} x${v.nodes.length}`);
    expect(graves, `violaciones en la mesa del Culo: ${graves.join(', ')}`).toEqual([]);
  });
});
