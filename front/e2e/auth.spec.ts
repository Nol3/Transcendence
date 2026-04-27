import { test, expect } from '@playwright/test';
import {
  bootAuthenticated,
  mockAuthLogin,
  mockAuthMe,
  mockAuthRefresh,
  mockAuthLogout,
  mockLeaderboard,
  setAuthToken,
  spaNavigate,
} from './helpers';

test.describe('Auth — login', () => {
  test('renders login form', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('shows validation errors on empty submit', async ({ page }) => {
    await page.goto('/login');
    await page.locator('button[type="submit"]').click();
    await expect(page.locator('.field--error')).toHaveCount(2);
  });

  test('successful login redirects to home', async ({ page }) => {
    await mockAuthLogin(page);
    await mockAuthMe(page);
    await mockAuthRefresh(page);
    await mockAuthLogout(page);
    // Home page calls leaderboard after login — mock it to prevent 401→logout cascade
    await mockLeaderboard(page);
    await page.goto('/login');
    await page.locator('input[type="email"]').fill('test@example.com');
    await page.locator('input[type="password"]').fill('password123');
    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL('/', { timeout: 8000 });
  });

  test('guest guard redirects authenticated user away from /login', async ({ page }) => {
    await setAuthToken(page);
    await mockAuthMe(page);
    await mockAuthRefresh(page);
    await mockAuthLogout(page);
    await mockLeaderboard(page);
    // waitForResponse MUST be set up before goto to avoid missing the response
    await bootAuthenticated(page);
    await spaNavigate(page, '/login');
    await expect(page).toHaveURL('/', { timeout: 5000 });
  });
});

test.describe('Auth — register', () => {
  test('renders register form', async ({ page }) => {
    await page.goto('/register');
    await expect(page.locator('form')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('guest guard redirects authenticated user away from /register', async ({ page }) => {
    await setAuthToken(page);
    await mockAuthMe(page);
    await mockAuthRefresh(page);
    await mockAuthLogout(page);
    await mockLeaderboard(page);
    await bootAuthenticated(page);
    await spaNavigate(page, '/register');
    await expect(page).toHaveURL('/', { timeout: 5000 });
  });
});
