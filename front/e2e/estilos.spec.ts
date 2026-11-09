import { expect, test } from '@playwright/test';

/**
 * Regresión del fallo del 09-11-2026: Angular publica el CSS principal como
 * `<link media="print" onload="this.media='all'">` cuando `inlineCritical` está activo, y la CSP
 * (`script-src 'self'`, sin `'unsafe-inline'`) **bloquea ese `onload`**: la hoja se queda en
 * `print` y el sitio real se ve solo con el CSS crítico incrustado.
 *
 * Los e2e no lo veían porque `quitarCspDeLosDocumentos()` quita la cabecera y entonces el
 * `onload` sí corre. Este test **no** toca la CSP a propósito.
 */
test('el CSS principal se aplica aunque haya CSP', async ({ page }) => {
  await page.goto('/login', { waitUntil: 'networkidle' });

  // 1. Ninguna hoja de estilos puede quedarse en `print` (sería CSS que no se aplica).
  const medios = await page.evaluate(() =>
    [...document.styleSheets].filter((s) => s.href).map((s) => s.media.mediaText),
  );
  expect(medios, 'hay una hoja cargada como "print" (el onload está bloqueado)').not.toContain('print');

  // 2. Y se nota: el ojo de «ver contraseña» solo tiene tamaño si la hoja global entra
  //    (sin ella mide 22×16, por debajo del mínimo de 24 de WCAG 2.5.8).
  const ojo = await page.locator('.field__toggle').boundingBox();
  expect(ojo?.width ?? 0).toBeGreaterThanOrEqual(24);
  expect(ojo?.height ?? 0).toBeGreaterThanOrEqual(24);
});
