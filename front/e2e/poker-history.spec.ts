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
 * Historial de póker (5.3): estadísticas, lista de partidas y las manos de cada
 * una. Se mockean los tres endpoints del historial.
 */
const stats = {
  hands_played: 12,
  hands_won: 5,
  showdowns: 6,
  showdowns_won: 2,
  biggest_pot: 240,
  folded: 4,
  win_rate: 41.7,
};

const match = {
  game_id: 1,
  opponent: { id: 2, username: 'rival' },
  result: 'win',
  my_stack: 1400,
  opponent_stack: 600,
  hands: 3,
  rated: true,
  played_at: '2026-07-01T10:00:00Z',
};

// Logros del póker (7.1): uno conseguido, la escalera de color y la racha a medias.
const achievements = {
  unlocked: 1,
  total: 3,
  achievements: [
    { id: 'primera_mano', unlocked: true, progress: 5, target: 1 },
    { id: 'escalera_de_color', unlocked: false, progress: 0, target: 1 },
    { id: 'tres_seguidas', unlocked: false, progress: 2, target: 3 },
  ],
};

const hands = [
  {
    id: 11,
    hand_number: 1,
    board: '7c 2s Ad Td 9d',
    pot: 240,
    showdown: true,
    winner_names: 'testuser',
    created_at: '2026-07-01T10:00:00Z',
    players: [
      {
        seat: 0,
        name: 'testuser',
        is_bot: false,
        hole: '8c Ts',
        hand_name: 'Pareja',
        stack_after: 1400,
        won: 240,
        folded: false,
      },
      {
        seat: 1,
        name: 'rival',
        is_bot: false,
        hole: '4h 5d',
        hand_name: 'Carta alta',
        stack_after: 600,
        won: 0,
        folded: false,
      },
    ],
  },
];

/** Registro de acciones de la primera mano, para el replay (roadmap 7.2). */
const acciones = [
  { event: 'hand_start', button: 0, sb: 10, bb: 20, stacks: [1000, 1000] },
  { event: 'blind', seat: 0, kind: 'small', amount: 10 },
  { event: 'blind', seat: 1, kind: 'big', amount: 20 },
  { event: 'action', seat: 0, action: 'raise', amount: 60, committed: 60, street: 'preflop' },
  { event: 'street', street: 'flop', board: ['7c', '2s', 'Ad'] },
  { event: 'action', seat: 1, action: 'fold', amount: 0, committed: 20, street: 'flop' },
  { event: 'uncalled_return', seat: 0, amount: 40 },
  { event: 'hand_end', winner: 0, amount: 90, showdown: false },
];

test.describe('Historial de póker', () => {
  test.beforeEach(async ({ page }) => {
    await setAuthToken(page);
    await mockAuthMe(page);
    await mockAuthRefresh(page);
    await mockAuthLogout(page);
    await mockLeaderboard(page);

    await page.route('**/poker/stats/', (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(stats) }),
    );
    await page.route('**/poker/history/*/', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ game_id: 1, results: hands }),
      }),
    );
    // Ojo con el orden: `**/poker/history/*/` solo cubre un segmento, así que la ruta
    // de una mano concreta (`history/hand/7/`) necesita su propio mock.
    await page.route('**/poker/history/hand/*/', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ...hands[0], actions: acciones }),
      }),
    );
    await page.route('**/poker/achievements/', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(achievements),
      }),
    );
    await page.route('**/poker/history/', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ count: 1, results: [match] }),
      }),
    );

    await bootAuthenticated(page);
  });

  test('muestra estadísticas y la lista de partidas', async ({ page }) => {
    await spaNavigate(page, '/poker/history');
    await expect(page.locator('.history-page')).toBeVisible({ timeout: 5000 });

    await expect(page.locator('.stats__row')).toHaveCount(5);
    await expect(page.locator('.stats')).toContainText('41.7');
    await expect(page.locator('.stats')).toContainText('240');

    const fila = page.locator('.matches__item').first();
    await expect(fila).toContainText('rival');
    await expect(fila).toContainText('3');
  });

  test('los logros del póker se ven y distinguen los conseguidos', async ({ page }) => {
    await spaNavigate(page, '/poker/history');
    await expect(page.locator('.history-page')).toBeVisible({ timeout: 5000 });

    const logros = page.locator('.logros__item');
    await expect(logros).toHaveCount(3);
    // El conseguido va marcado; los otros dos, apagados.
    await expect(page.locator('.logros__item--on')).toHaveCount(1);
    // El progreso es lo único que no depende del idioma del navegador.
    await expect(page.locator('.logros')).toContainText('2/3');
    // Y cada logro tiene su nombre (en el idioma que sea).
    for (const item of await logros.all()) {
      expect((await item.locator('.logros__name').innerText()).trim().length).toBeGreaterThan(0);
    }
  });

  test('abrir una partida muestra sus manos con cartas y ganador', async ({ page }) => {
    await spaNavigate(page, '/poker/history');
    await page.locator('.matches__item').first().click();

    await expect(page.locator('.hand')).toHaveCount(1, { timeout: 5000 });
    const mano = page.locator('.hand').first();
    await expect(mano).toContainText('#1');
    await expect(mano).toContainText('240');       // bote
    await expect(mano).toContainText('testuser');  // ganador
    // Cartas del tablero (5) + las de los dos jugadores (4), ya con el arte del mazo.
    await expect(mano.locator('.pc')).toHaveCount(9);
    // Y que las imágenes carguen de verdad, no que queden huecos vacíos.
    const cargadas = await mano.locator('.pc__cara').evaluateAll(
      (imgs: HTMLImageElement[]) => imgs.length > 0 && imgs.every((i) => i.naturalWidth > 0),
    );
    expect(cargadas).toBe(true);
    await expect(mano).toContainText('Pareja');
    await expect(mano).toContainText('Carta alta');
  });

  test('el replay reproduce la mano paso a paso', async ({ page }) => {
    await spaNavigate(page, '/poker/history');
    await page.locator('.matches__item').first().click();
    await expect(page.locator('.hand')).toHaveCount(1, { timeout: 5000 });

    // Abrir el replay: la mano se pide al abrirla, no al listar.
    await page.locator('.hand__replay-btn').first().click();
    const replay = page.locator('.replay');
    await expect(replay).toBeVisible();

    // Al principio no hay cartas en la mesa y el bote está a cero.
    await expect(replay.locator('.replay__tablero .pc')).toHaveCount(0);
    await expect(replay.locator('.replay__bote')).toContainText('0');

    // Controles: ⏮ ◀ ▶(play) ▶ ⏭ — se avanza con el cuarto botón.
    const botones = replay.locator('.replay__controles button');
    await botones.nth(3).click();
    await botones.nth(3).click();
    await botones.nth(3).click();
    // 10 (ciega) + 20 (ciega) + 60 (subida) = 90
    await expect(replay.locator('.replay__bote')).toContainText('90');

    // Al final: aparecen las tres comunitarias, el bote descuenta lo no igualado
    // (90 - 40 = 50) y el registro tiene las siete jugadas (reparto, dos ciegas, la
    // subida, el flop, el retiro y el resultado).
    await botones.nth(4).click();
    await expect(replay.locator('.replay__tablero .pc')).toHaveCount(3);
    await expect(replay.locator('.replay__bote')).toContainText('50');
    await expect(replay.locator('.replay__jugada')).toHaveCount(7);

    // Y se cierra.
    await replay.locator('.replay__cerrar').click();
    await expect(page.locator('.replay')).toHaveCount(0);
  });

  test('sin partidas muestra el estado vacío', async ({ page }) => {
    await page.route('**/poker/history/', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ count: 0, results: [] }),
      }),
    );
    await spaNavigate(page, '/poker/history');
    await expect(page.locator('.history-page')).toBeVisible({ timeout: 5000 });
    await expect(page.getByText(/not played a poker match/i)).toBeVisible();
  });
});
