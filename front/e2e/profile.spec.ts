import { test, expect } from '@playwright/test';
import {
  bootAuthenticated,
  mockAuthMe,
  mockAuthRefresh,
  mockAuthLogout,
  mockLeaderboard,
  setAuthToken,
  spaNavigate,
} from './helpers';

test.describe('Profile — auth guard', () => {
  test('unauthenticated /profile redirects to /login', async ({ page }) => {
    await page.route('**/auth/me', (route) => route.fulfill({ status: 401, body: '{}' }));
    await page.goto('/profile');
    await expect(page).toHaveURL('/login');
  });
});

test.describe('Profile — authenticated', () => {
  test.beforeEach(async ({ page }) => {
    await setAuthToken(page);
    await mockAuthMe(page);
    await mockAuthRefresh(page);
    await mockAuthLogout(page);
    await mockLeaderboard(page);
    await page.route('**/users/me/stats**', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: { wins: 10, losses: 5, totalGames: 15, winRate: 67 },
          error: null,
        }),
      }),
    );
    await page.route('**/users/me/history**', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ data: { results: [], count: 0 }, error: null }),
      }),
    );
    // waitForResponse BEFORE goto — response arrives during page load
    await bootAuthenticated(page);
  });

  test('renders profile page', async ({ page }) => {
    await spaNavigate(page, '/profile');
    await expect(page).toHaveURL('/profile', { timeout: 5000 });
    await expect(page.locator('app-profile').first()).toBeVisible({ timeout: 5000 });
  });
});
