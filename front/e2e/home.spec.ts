import { test, expect } from '@playwright/test';
import { mockLeaderboard } from './helpers';

test.describe('Home', () => {
  test.beforeEach(async ({ page }) => {
    // Block auth/me so app starts unauthenticated
    await page.route('**/auth/me', (route) => route.fulfill({ status: 401, body: '{}' }));
    await mockLeaderboard(page);
  });

  test('renders hero section', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('.hero')).toBeVisible();
  });

  test('renders leaderboard card', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('.leaderboard-card')).toBeVisible();
  });

  test('leaderboard shows rows after loading', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('.leaderboard__row').first()).toBeVisible({ timeout: 5000 });
    await expect(page.locator('.leaderboard__row')).toHaveCount(3);
  });

  test('leaderboard shows player names', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('.leaderboard__name').first()).toContainText('player1');
  });

  test('unauthenticated: shows login button in hero', async ({ page }) => {
    await page.goto('/');
    // app-button renders <button> not <a>, so match the custom element within the hero
    await expect(page.locator('.hero app-button').first()).toBeVisible();
  });
});
