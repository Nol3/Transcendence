import { test, expect } from '@playwright/test';
import {
  bootAuthenticated,
  mockAuthMe,
  mockAuthRefresh,
  mockAuthLogout,
  mockLeaderboard,
  mockTournaments,
  setAuthToken,
  spaNavigate,
} from './helpers';

test.describe('Tournaments — auth guard', () => {
  test('unauthenticated /tournament redirects to /login', async ({ page }) => {
    await page.route('**/auth/me', (route) => route.fulfill({ status: 401, body: '{}' }));
    await page.goto('/tournament');
    await expect(page).toHaveURL('/login');
  });
});

test.describe('Tournaments — authenticated', () => {
  test.beforeEach(async ({ page }) => {
    await setAuthToken(page);
    await mockAuthMe(page);
    await mockAuthRefresh(page);
    await mockAuthLogout(page);
    await mockLeaderboard(page);
    await mockTournaments(page);
    // waitForResponse BEFORE goto — response arrives during page load
    await bootAuthenticated(page);
  });

  test('renders tournament page', async ({ page }) => {
    await spaNavigate(page, '/tournament');
    await expect(page).toHaveURL('/tournament', { timeout: 5000 });
    await expect(page.locator('app-tournament').first()).toBeVisible({ timeout: 5000 });
  });

  test('shows empty state when no tournaments', async ({ page }) => {
    await spaNavigate(page, '/tournament');
    await expect(page).toHaveURL('/tournament', { timeout: 5000 });
    // Template renders <div class="empty-state arcade-panel"> via @empty block
    await expect(page.locator('.empty-state, [class*="empty"]')).toBeVisible({ timeout: 5000 });
  });

  test('create tournament button is visible', async ({ page }) => {
    await spaNavigate(page, '/tournament');
    await expect(page).toHaveURL('/tournament', { timeout: 5000 });
    // Button text is "+ Create Tournament"
    const createBtn = page.getByRole('button', { name: /create/i });
    await expect(createBtn).toBeVisible({ timeout: 5000 });
  });
});
