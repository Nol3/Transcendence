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
 * Página de chat (antes solo existía la API).
 *
 * Se mockean los endpoints del chat: la lista de mensajes, el directorio de
 * usuarios, el envío y el marcado como leído. Lo que se comprueba es que la UI
 * agrupa por conversación, abre el hilo y envía.
 */
const rival = { id: 2, username: 'rival', avatar: null };
const yo = { id: 1, username: 'testuser', avatar: null };

function mensaje(id: number, de: typeof yo, para: typeof yo, texto: string, leido = true) {
  return {
    id,
    sender: de,
    recipient: para,
    content: texto,
    created_at: new Date(2026, 6, 1, 10, id).toISOString(),
    is_read: leido,
  };
}

test.describe('Chat', () => {
  test.beforeEach(async ({ page }) => {
    await setAuthToken(page);
    await mockAuthMe(page);
    await mockAuthRefresh(page);
    await mockAuthLogout(page);
    await mockLeaderboard(page);

    await page.route('**/chat/messages/**', (route) => {
      const url = route.request().url();
      const json = (body: unknown) =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });

      if (url.includes('/send_message/')) {
        const enviado = JSON.parse(route.request().postData() ?? '{}');
        return json(mensaje(99, yo, rival, enviado.content, false));
      }
      if (url.includes('/mark_read/')) return json({ marked_read: 1 });
      return json({
        count: 2,
        next: null,
        previous: null,
        results: [
          mensaje(2, rival, yo, '¿jugamos un torneo?', false),
          mensaje(1, yo, rival, 'hola', true),
        ],
      });
    });
    await page.route('**/users/', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          count: 1,
          next: null,
          previous: null,
          results: [{ id: 3, username: 'otro', avatar: null }],
        }),
      }),
    );

    await bootAuthenticated(page);
  });

  test('agrupa por conversación y muestra los sin leer', async ({ page }) => {
    await spaNavigate(page, '/chat');
    // El título es un componente pixelado (el texto va troceado en spans), así que
    // se comprueba el contenedor de la página, no el literal.
    await expect(page.locator('.chat-page')).toBeVisible({ timeout: 5000 });

    await expect(page.locator('.convs__name', { hasText: 'rival' })).toBeVisible();
    await expect(page.locator('.convs__last')).toContainText('¿jugamos un torneo?');
    await expect(page.locator('.convs__badge')).toHaveText('1');
  });

  test('abrir la conversación muestra el hilo y permite responder', async ({ page }) => {
    await spaNavigate(page, '/chat');
    await page.getByRole('button', { name: /rival/ }).first().click();

    // El hilo se pinta con los dos mensajes (el mío y el suyo).
    await expect(page.locator('.thread__bubble')).toHaveCount(2, { timeout: 5000 });
    await expect(page.locator('.thread__text', { hasText: 'hola' })).toBeVisible();

    await page.locator('.compose__input').fill('nos vemos en la mesa');
    await page.getByRole('button', { name: /send/i }).click();

    // El mensaje enviado entra en el hilo (lo devuelve el mock).
    await expect(page.locator('.thread__text', { hasText: 'nos vemos en la mesa' })).toBeVisible({
      timeout: 5000,
    });
  });

  test('se puede empezar una conversación con otro jugador', async ({ page }) => {
    await spaNavigate(page, '/chat');
    await page.getByRole('button', { name: /new conversation/i }).click();
    await page.getByPlaceholder(/search player/i).fill('otro');
    await expect(page.getByRole('button', { name: /otro/ })).toBeVisible();
  });

  test('sin sesión redirige al login', async ({ page }) => {
    // Contexto limpio (sin el token del beforeEach) para probar el guard.
    const ctx = await page.context().browser()!.newContext();
    const anon = await ctx.newPage();
    await anon.route('**/auth/me', (route) => route.fulfill({ status: 401, body: '{}' }));
    await anon.goto('/chat');
    await expect(anon).toHaveURL(/\/login/, { timeout: 5000 });
    await ctx.close();
  });
});
