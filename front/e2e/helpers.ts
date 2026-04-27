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
  // TournamentService uses HttpClient directly (not ApiService), expects a plain array
  await page.route(/\/tournament/, (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    }),
  );
}

/**
 * No-op kept for spec compatibility. Real auth seeding happens inside bootAuthenticated()
 * via the login flow because pre-seeding localStorage triggers a circular-DI bug in
 * AuthService initAuth → http interceptor → inject(AuthService) chain.
 */
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
  await page.goto('/login');
  await page.locator('input[type="email"]').fill('test@example.com');
  await page.locator('input[type="password"]').fill('password123');
  await page.locator('button[type="submit"]').click();
  await page.waitForURL('/', { timeout: 8000 });
  await page.waitForLoadState('networkidle');
}
