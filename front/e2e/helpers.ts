import { Page } from '@playwright/test';

const MOCK_USER = {
  id: 1,
  username: 'testuser',
  email: 'test@example.com',
  avatar: null,
  wins: 10,
  losses: 5,
  totalGames: 15,
};

const MOCK_TOKENS = {
  accessToken: 'mock-access-token',
  refreshToken: 'mock-refresh-token',
};

export async function mockAuthMe(page: Page) {
  await page.route('**/auth/me', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ data: { user: MOCK_USER }, error: null }),
    }),
  );
}

export async function mockAuthLogin(page: Page) {
  await page.route('**/auth/login', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ data: { user: MOCK_USER, tokens: MOCK_TOKENS }, error: null }),
    }),
  );
}

export async function mockAuthRefresh(page: Page) {
  // Prevent the auth interceptor's 401→refresh→logout cascade by returning valid tokens
  await page.route('**/auth/refresh', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ data: { tokens: MOCK_TOKENS }, error: null }),
    }),
  );
}

export async function mockAuthLogout(page: Page) {
  await page.route('**/auth/logout', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: '{}' }),
  );
}

export async function mockLeaderboard(page: Page) {
  const entries = Array.from({ length: 3 }, (_, i) => ({
    rank: i + 1,
    user: { id: i + 1, username: `player${i + 1}`, avatar: null },
    wins: 10 - i,
    losses: i,
    winRate: Math.round(((10 - i) / 10) * 100),
    totalGames: 10,
  }));
  await page.route('**/leaderboard*', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: entries,
        meta: { page: 1, limit: 10, total: 3, totalPages: 1 },
        error: null,
      }),
    }),
  );
}

export async function mockTournaments(page: Page) {
  // TournamentService espera la respuesta PAGINADA de DRF ({results: [...]}), no
  // un array plano: con un array, `response.results.map(...)` revienta y la lista
  // se queda vacía (por eso los e2e del bracket no encontraban el botón).
  await page.route(/\/tournament/, (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ count: 0, next: null, previous: null, results: [] }),
    }),
  );
}

/**
 * Mock a full in-progress tournament owned by the current user (id 1) with a
 * single pending final, plus the detail GET and the match-result POST. Register
 * AFTER mockTournaments so this more specific handler takes precedence.
 */
export async function mockTournamentFlow(page: Page) {
  const player1 = { id: 1, username: 'testuser', avatar: null };
  const player2 = { id: 2, username: 'rival', avatar: null };
  const baseMatch = {
    id: 10,
    round: 1,
    position: 0,
    player1,
    player2,
    winner_slot: null as 1 | 2 | null,
    player1_score: 0,
    player2_score: 0,
    status: 'pending' as 'pending' | 'live' | 'completed',
  };
  const tournament = {
    id: 1,
    name: 'E2E Cup',
    description: '',
    creator: player1,
    max_players: 4,
    status: 'in_progress',
    winner: null as null | typeof player1,
    created_at: '2026-06-30T10:00:00Z',
    started_at: '2026-06-30T10:05:00Z',
    finished_at: null as string | null,
    participants: [
      { id: 1, user: player1, is_eliminated: false, joined_at: '2026-06-30T10:00:00Z' },
      { id: 2, user: player2, is_eliminated: false, joined_at: '2026-06-30T10:01:00Z' },
    ],
    rounds: [{ id: 1, number: 1, name: 'Final', matches: [baseMatch] }],
  };

  await page.route(/\/tournament/, (route) => {
    const req = route.request();
    const url = req.url();
    const json = (body: unknown) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });

    if (req.method() === 'POST' && /\/matches\/\d+\/result\/?(\?|$)/.test(url)) {
      const finished = {
        ...tournament,
        status: 'finished',
        winner: player1,
        finished_at: '2026-06-30T10:30:00Z',
        rounds: [
          {
            ...tournament.rounds[0],
            matches: [
              {
                ...baseMatch,
                winner_slot: 1,
                player1_score: 1,
                player2_score: 0,
                status: 'completed',
              },
            ],
          },
        ],
      };
      return json(finished);
    }
    if (req.method() === 'GET' && /\/tournament\/1\/?(\?|$)/.test(url)) {
      return json(tournament);
    }
    // Lista: mismo sobre paginado que devuelve DRF.
    return json({ count: 1, next: null, previous: null, results: [tournament] });
  });
}

/**
 * No-op kept for spec compatibility. Real auth seeding happens inside bootAuthenticated()
 * via the login flow because pre-seeding localStorage triggers a circular-DI bug in
 * AuthService initAuth → http interceptor → inject(AuthService) chain.
 */
/**
 * Quita la cabecera `Content-Security-Policy` **solo de los documentos** de la página.
 *
 * axe se inyecta como script en la página y `script-src 'self'` lo bloquea, así que sin esto
 * los tests de accesibilidad fallan por la política y no por la accesibilidad. Es legítimo
 * hacerlo aquí: la inyección de axe es la herramienta de auditoría, no un flujo de usuario.
 * De que la política se envíe de verdad ya se encargan los tests del backend (`CspTests`) y
 * la comprobación con `curl` contra el stack.
 */
export async function quitarCspDeLosDocumentos(page: Page): Promise<void> {
  await page.route('**/*', async (route) => {
    if (route.request().resourceType() !== 'document') return route.continue();
    const respuesta = await route.fetch();
    const cabeceras = { ...respuesta.headers() };
    delete cabeceras['content-security-policy'];
    await route.fulfill({ response: respuesta, headers: cabeceras });
  });
}

export async function setAuthToken(_page: Page) {
  // intentionally empty
}

/**
 * Trigger Angular SPA navigation without a full page reload.
 * Use after auth state is established (page loaded at '/' + /auth/me resolved).
 * This avoids the race condition between initAuth() and synchronous guards.
 */
export async function spaNavigate(page: Page, path: string): Promise<void> {
  await page.evaluate((p) => {
    window.history.pushState({}, '', p);
    window.dispatchEvent(new PopStateEvent('popstate', { state: null }));
  }, path);
}

/**
 * Boot app authenticated by going through the login form.
 * Avoids the circular-DI issue where AuthService construction with a token in localStorage
 * triggers fetchCurrentUser() whose interceptor tries to inject the still-constructing AuthService,
 * causing initAuth's error handler to clearTokens before /auth/me ever fires.
 *
 * Login flow path: goto('/login') → AuthService constructs without token (clean) →
 * submit form → mock /auth/login responds → AuthService sets _user + tokens → router redirects to /.
 * Caller MUST register mockAuthLogin + mockAuthMe + mockAuthRefresh + mockAuthLogout + mockLeaderboard before calling.
 */
export async function bootAuthenticated(page: Page): Promise<void> {
  await mockAuthLogin(page);
  // Home page calls getUserStats() after login — mock to prevent 401→logout cascade
  await page.route('**/users/me/stats**', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: { wins: 10, losses: 5, rank: 1, winRate: 67, gamesPlayed: 15, currentStreak: 3, longestStreak: 5 },
        error: null,
      }),
    }),
  );
  await page.goto('/login');
  await page.locator('input[type="email"]').fill('test@example.com');
  await page.locator('input[type="password"]').fill('password123');
  await page.locator('button[type="submit"]').click();
  await page.waitForURL('/', { timeout: 8000 });
  await page.waitForLoadState('networkidle');
}
/**
 * Mock de un match con resultado DECLARADO por el rival y pendiente de que el
 * usuario actual lo confirme (estado `awaiting_confirmation`). Registra la ruta
 * del POST de resultado para que, al confirmar, el match quede completado.
 */
export async function mockTournamentPendingConfirmation(page: Page) {
  const me = { id: 1, username: 'testuser', avatar: null };
  const rival = { id: 2, username: 'rival', avatar: null };
  const pendingMatch = {
    id: 10,
    round: 1,
    position: 0,
    player1: me,
    player2: rival,
    winner_slot: null,
    player1_score: 0,
    player2_score: 0,
    status: 'awaiting_confirmation',
    reported_winner_slot: 2, // el rival dice que gana él
    reported_by: { id: 2, username: 'rival' },
  };
  const base = {
    id: 1,
    name: 'E2E Cup',
    description: '',
    creator: me,
    max_players: 4,
    status: 'in_progress',
    winner: null,
    created_at: '2026-06-30T10:00:00Z',
    started_at: '2026-06-30T10:05:00Z',
    finished_at: null,
    participants: [
      { id: 1, user: me, is_eliminated: false, joined_at: '2026-06-30T10:00:00Z' },
      { id: 2, user: rival, is_eliminated: false, joined_at: '2026-06-30T10:01:00Z' },
    ],
    rounds: [{ id: 1, number: 1, name: 'Final', matches: [pendingMatch] }],
  };

  await page.route(/\/tournament/, (route) => {
    const req = route.request();
    const url = req.url();
    const json = (body: unknown) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });

    if (req.method() === 'POST' && /\/matches\/\d+\/result\/?/.test(url)) {
      return json({
        ...base,
        rounds: [
          {
            ...base.rounds[0],
            matches: [
              {
                ...pendingMatch,
                status: 'completed',
                winner_slot: 2,
                player1_score: 0,
                player2_score: 1,
              },
            ],
          },
        ],
      });
    }
    if (req.method() === 'GET' && /\/tournament\/1\/?/.test(url)) return json(base);
    return json({ count: 1, next: null, previous: null, results: [base] });
  });
}

