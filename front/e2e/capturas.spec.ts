// Capturas para revisar el aspecto de las cartas nuevas (temporal, no forma parte de
// la suite: se ejecuta a mano cuando se quiere mirar el resultado).
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

const SALIDA = 'capturas';

const acciones = [
  { event: 'hand_start', button: 0, sb: 10, bb: 20, stacks: [1000, 1000] },
  { event: 'blind', seat: 0, kind: 'small', amount: 10 },
  { event: 'blind', seat: 1, kind: 'big', amount: 20 },
  { event: 'action', seat: 0, action: 'raise', amount: 60, committed: 60, street: 'preflop' },
  { event: 'street', street: 'flop', board: ['7c', '2s', 'Ad'] },
  { event: 'action', seat: 1, action: 'call', amount: 60, committed: 60, street: 'flop' },
  { event: 'street', street: 'turn', board: ['7c', '2s', 'Ad', 'Td'] },
  { event: 'hand_end', winner: 0, amount: 160, showdown: true },
];

const mano = {
  id: 1,
  hand_number: 1,
  board: '7c 2s Ad Td 9d',
  pot: 240,
  showdown: true,
  winner_names: 'testuser',
  created_at: '2026-10-13T10:00:00Z',
  players: [
    { seat: 0, name: 'testuser', is_bot: false, hole: 'Ah Kh', hand_name: 'Pareja', stack_after: 1240, won: 240, folded: false },
    { seat: 1, name: 'Bot Rival', is_bot: true, hole: '3c 8d', hand_name: 'Carta alta', stack_after: 760, won: 0, folded: true },
  ],
};

test('captura de las cartas', async ({ page }) => {
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
  await page.route('**/poker/history/hand/*/', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ...mano, actions: acciones }) }),
  );
  await page.route('**/poker/history/*/', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ game_id: 1, results: [mano] }) }),
  );
  await page.route('**/poker/history/', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        count: 1,
        results: [{
          game_id: 1, opponent: { id: 2, username: 'Bot Rival' }, result: 'win',
          my_stack: 1240, opponent_stack: 760, hands: 1, rated: true, played_at: '2026-10-13T10:00:00Z',
        }],
      }),
    }),
  );
  await page.route('**/poker/stats/', (route) =>
    route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({ hands_played: 12, hands_won: 5, showdowns: 4, showdowns_won: 3, biggest_pot: 480, folded: 2, win_rate: 42 }),
    }),
  );
  await page.route('**/poker/achievements/', (route) =>
    route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({ unlocked: 1, total: 3, achievements: [
        { id: 'primera_mano', unlocked: true, progress: 1, target: 1 },
        { id: 'escalera_de_color', unlocked: false, progress: 0, target: 1 },
        { id: 'tres_seguidas', unlocked: false, progress: 2, target: 3 },
      ] }),
    }),
  );

  await bootAuthenticated(page);

  // El apartado de juegos, que es donde entra un juego nuevo.
  await spaNavigate(page, '/games');
  await page.locator('.game-card').first().waitFor();
  await page.waitForTimeout(900);
  await page.screenshot({ path: `${SALIDA}/0-apartado-juegos.png`, fullPage: false });

  // El Culo: ajustes, mesa repartida y las reglas.
  await spaNavigate(page, '/culo');
  await page.locator('.inicio').waitFor();
  await page.waitForTimeout(700);
  await page.screenshot({ path: `${SALIDA}/4-culo-ajustes.png`, fullPage: false });

  await page.locator('.culo__acciones button').first().click();
  await expect(page.locator('.reglas')).toBeVisible();
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${SALIDA}/5-culo-reglas.png`, fullPage: false });
  await page.locator('.reglas__cerrar').click();

  await page.locator('.modo__local button').click();
  await expect(page.locator('.mesa')).toBeVisible();
  await page.waitForTimeout(1200);   // que entren las cartas y juegue el primer bot
  await page.screenshot({ path: `${SALIDA}/6-culo-mesa.png`, fullPage: false });

  await spaNavigate(page, '/poker/history');
  await page.locator('.matches__item').first().click();
  await page.locator('.hand').first().waitFor();
  // Además de la captura, comprueba lo único que no se ve en el código: que los PNG
  // del mazo se sirvan y se pinten.
  await expect(page.locator('.pc__cara').first()).toBeVisible();
  await page.waitForTimeout(900);
  await page.screenshot({ path: `${SALIDA}/1-historial-cartas.png`, fullPage: false });

  // El replay, a mitad y al final (donde se ven las cinco comunitarias).
  await page.locator('.hand__replay-btn').first().click();
  const replay = page.locator('.replay');
  await replay.waitFor();
  const cargadas = await replay.locator('.pc__cara').evaluateAll(
    (imgs: HTMLImageElement[]) => imgs.every((i) => i.naturalWidth > 0),
  );
  expect(cargadas).toBe(true);
  const botones = replay.locator('.replay__controles button');
  await botones.nth(4).click();
  await page.waitForTimeout(700);
  await page.screenshot({ path: `${SALIDA}/2-replay-final.png`, fullPage: false });

  // Y una carta de cerca, para ver el pixel art y el brillo.
  await replay.locator('.pc').nth(2).hover();
  await page.waitForTimeout(400);
  await replay.locator('.replay__mesa').screenshot({ path: `${SALIDA}/3-cartas-cerca.png` });
});
