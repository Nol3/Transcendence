import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env['CI'],
  retries: process.env['CI'] ? 2 : 0,
  workers: process.env['CI'] ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:4200',
    trace: 'on-first-retry',
    // Los e2e trabajan con la API simulada, y el service worker (PWA, 7.4) sirve
    // respuestas de su propia caché y se salta esos mocks: sin esto, el login
    // simulado no redirige y los tests se quedan esperando. La PWA se verifica aparte,
    // con `node scripts/audit/probe_pwa.js`, que sí necesita el worker de verdad.
    serviceWorkers: 'block',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
      // El spec móvil necesita pantalla pequeña y dedo: corre solo en el proyecto `movil`.
      testIgnore: /movil\.spec\.ts/,
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
      testIgnore: /movil\.spec\.ts/,
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
      testIgnore: /movil\.spec\.ts/,
    },
    {
      // Edge no lo puede instalar Playwright: usa el del sistema (Windows).
      name: 'msedge',
      use: { ...devices['Desktop Edge'], channel: 'msedge' },
      testIgnore: /movil\.spec\.ts/,
    },
    {
      // Móvil de verdad: pantalla pequeña, dedo inalámbrico. Solo corre lo marcado con @movil,
      // para no duplicar la suite entera en cada pasada (`npx playwright test --project=movil`).
      name: 'movil',
      use: { ...devices['Pixel 7'] },
      grep: /@movil/,
    },
  ],
  webServer: {
    command: 'npm run start',
    url: 'http://localhost:4200',
    reuseExistingServer: !process.env['CI'],
    timeout: 120_000,
  },
});
