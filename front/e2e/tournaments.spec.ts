import { test, expect } from '@playwright/test';
import {
  bootAuthenticated,
  mockAuthMe,
  mockAuthRefresh,
  mockAuthLogout,
  mockLeaderboard,
  mockTournaments,
  mockTournamentFlow,
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

test.describe('Tournaments — bracket flow', () => {
  test.beforeEach(async ({ page }) => {
    await setAuthToken(page);
    await mockAuthMe(page);
    await mockAuthRefresh(page);
    await mockAuthLogout(page);
    await mockLeaderboard(page);
    await mockTournaments(page);
    await bootAuthenticated(page);
    // More specific tournament mocks win over the empty-list one above.
    await mockTournamentFlow(page);
    // currentUserId is read from localStorage 'user' when the component builds.
    await page.evaluate(() =>
      localStorage.setItem('user', JSON.stringify({ id: 1, username: 'testuser' })),
    );
  });

  test('opens bracket from the active tab and shows match actions', async ({ page }) => {
    await spaNavigate(page, '/tournament');
    await expect(page).toHaveURL('/tournament', { timeout: 5000 });

    // The in-progress tournament shows under the default "active" tab.
    await page.getByRole('button', { name: /view bracket/i }).click();

    await expect(page.locator('app-bracket')).toBeVisible({ timeout: 5000 });
    // Current user (creator + player) gets a "Jugar" action on the pending match.
    await expect(page.getByRole('button', { name: /jugar/i }).first()).toBeVisible({
      timeout: 5000,
    });
  });

  test('reporting a winner completes the match', async ({ page }) => {
    await spaNavigate(page, '/tournament');
    await expect(page).toHaveURL('/tournament', { timeout: 5000 });

    await page.getByRole('button', { name: /view bracket/i }).click();
    await expect(page.locator('app-bracket')).toBeVisible({ timeout: 5000 });

    // Report the current user as winner via the bracket's winner button.
    await page.getByRole('button', { name: 'testuser', exact: true }).first().click();

    // Backend mock returns the finished bracket → match renders as completed.
    await expect(page.locator('.bracket__match--completed').first()).toBeVisible({
      timeout: 5000,
    });
  });

  test('deep link /tournament/:id opens the detail view', async ({ page }) => {
    await spaNavigate(page, '/tournament/1');
    await expect(page.locator('app-bracket')).toBeVisible({ timeout: 5000 });
  });
});
