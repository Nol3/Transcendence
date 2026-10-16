import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
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
 * Auditoría de accesibilidad con axe (roadmap 7.3).
 *
 * Recorre las pantallas principales y falla solo por lo **grave** (`critical` y
 * `serious`): así el test es una red de seguridad útil y no una lista de deseos. Todo
 * lo que aparece se imprime, aunque no haga fallar el test, para poder ir mejorándolo.
 *
 * Los colores del tema neón dan avisos de contraste que se revisan a mano: cambiar la
 * paleta es una decisión de diseño, no un arreglo automático.
 */
const RUTAS = [
  { ruta: '/', nombre: 'inicio' },
  { ruta: '/games', nombre: 'juegos' },
  { ruta: '/culo', nombre: 'culo' },
  { ruta: '/mentiroso', nombre: 'mentiroso' },
  { ruta: '/brisca', nombre: 'brisca' },
  { ruta: '/tute', nombre: 'tute' },
  { ruta: '/mus', nombre: 'mus' },
  { ruta: '/poker', nombre: 'póker' },
  { ruta: '/poker/history', nombre: 'historial de póker' },
  { ruta: '/tournament', nombre: 'torneos' },
  { ruta: '/profile', nombre: 'perfil' },
  { ruta: '/chat', nombre: 'chat' },
];

test.describe('Accesibilidad (axe)', () => {
  test.beforeEach(async ({ page }) => {
    // axe se inyecta como script y la CSP lo bloquearía (ver el helper).
    await quitarCspDeLosDocumentos(page);

    // Comodín para que las pantallas pinten su estructura aunque no haya datos: los
    // mocks concretos de los helpers se registran después y tienen prioridad.
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

  for (const { ruta, nombre } of RUTAS) {
    test(`${nombre} no tiene violaciones graves`, async ({ page }) => {
      await spaNavigate(page, ruta);
      await page.waitForTimeout(600);   // deja que la vista termine de montarse

      const informe = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa'])
        .analyze();

      if (informe.violations.length) {
        const resumen = informe.violations
          .map((v) => `${v.id} [${v.impact}] x${v.nodes.length}`)
          .join(', ');
        console.log(`  · ${nombre}: ${resumen}`);
        // Detalle de los primeros nodos, para poder arreglarlos sin adivinar.
        for (const v of informe.violations) {
          for (const nodo of v.nodes.slice(0, 3)) {
            const datos = nodo.any?.[0]?.data ?? {};
            const pista = datos.contrastRatio
              ? `contraste ${datos.contrastRatio} (fg ${datos.fgColor} sobre bg ${datos.bgColor})`
              : (datos.message ?? '');
            console.log(`      - ${v.id}: ${nodo.target.join(' ')} → ${String(pista).slice(0, 90)}`);
          }
        }
      }

      const graves = informe.violations
        .filter((v) => v.impact === 'critical' || v.impact === 'serious')
        .map((v) => `${v.id} x${v.nodes.length}`);
      expect(graves, `violaciones graves en ${nombre}`).toEqual([]);
    });
  }
});
