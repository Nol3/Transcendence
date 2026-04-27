---------------------------------- Hay errores que solucionar el Playwright Test - cd Transcendence/front && npx playwright test

tournaments.spec.ts
Tournaments — authenticated › renders tournament pagechromium
30.1s
tournaments.spec.ts:33
Tournaments — authenticated › shows empty state when no tournamentschromium
30.0s
tournaments.spec.ts:39
Tournaments — authenticated › create tournament button is visiblechromium
30.1s
tournaments.spec.ts:46
Tournaments — auth guard › unauthenticated /tournament redirects to /loginchromium
568ms
tournaments.spec.ts:14
auth.spec.ts
Auth — login › guest guard redirects authenticated user away from /loginchromium
30.1s
auth.spec.ts:41
Auth — register › guest guard redirects authenticated user away from /registerchromium
30.1s
auth.spec.ts:61
Auth — login › renders login formchromium
760ms
auth.spec.ts:14
Auth — login › shows validation errors on empty submitchromium
1.1s
auth.spec.ts:21
Auth — login › successful login redirects to homechromium
1.2s
auth.spec.ts:27
Auth — register › renders register formchromium
629ms
auth.spec.ts:55
profile.spec.ts
Profile — authenticated › renders profile pagechromium
30.1s
profile.spec.ts:48
Profile — auth guard › unauthenticated /profile redirects to /loginchromium
487ms
profile.spec.ts:13
home.spec.ts
Home › renders hero sectionchromium
852ms
home.spec.ts:11
Home › renders leaderboard cardchromium
920ms
home.spec.ts:16
Home › leaderboard shows rows after loadingchromium
557ms
home.spec.ts:21
Home › leaderboard shows player nameschromium
534ms
home.spec.ts:27
Home › unauthenticated: shows login button in herochromium
609ms
home.spec.ts:32

aleja@Nol3:/mnt/c/Users/aleja/Desktop/claude/Transcendence/front$ npx playwright test

Running 17 tests using 8 workers
  1) [chromium] › e2e/auth.spec.ts:41:7 › Auth — login › guest guard redirects authenticated user away from /login 

    Test timeout of 30000ms exceeded.

    Error: page.waitForResponse: Test timeout of 30000ms exceeded.
    =========================== logs ===========================
    waiting for response "**/auth/me"
    ============================================================

       at helpers.ts:112

      110 |  */
      111 | export async function bootAuthenticated(page: Page): Promise<void> {
    > 112 |   const authDone = page.waitForResponse('**/auth/me');
          |                         ^
      113 |   await page.goto('/');
      114 |   await authDone;
      115 | }
        at bootAuthenticated (/mnt/c/Users/aleja/Desktop/claude/Transcendence/front/e2e/helpers.ts:112:25)
        at /mnt/c/Users/aleja/Desktop/claude/Transcendence/front/e2e/auth.spec.ts:48:28

    Error Context: test-results/auth-Auth-—-login-guest-gu-783db-icated-user-away-from-login-chromium/error-context.md

  2) [chromium] › e2e/auth.spec.ts:61:7 › Auth — register › guest guard redirects authenticated user away from /register 

    Test timeout of 30000ms exceeded.

    Error: page.waitForResponse: Test timeout of 30000ms exceeded.
    =========================== logs ===========================
    waiting for response "**/auth/me"
    ============================================================

       at helpers.ts:112

      110 |  */
      111 | export async function bootAuthenticated(page: Page): Promise<void> {
    > 112 |   const authDone = page.waitForResponse('**/auth/me');
          |                         ^
      113 |   await page.goto('/');
      114 |   await authDone;
      115 | }
        at bootAuthenticated (/mnt/c/Users/aleja/Desktop/claude/Transcendence/front/e2e/helpers.ts:112:25)
        at /mnt/c/Users/aleja/Desktop/claude/Transcendence/front/e2e/auth.spec.ts:67:28

    Error Context: test-results/auth-Auth-—-register-guest-d9659-ted-user-away-from-register-chromium/error-context.md

  3) [chromium] › e2e/profile.spec.ts:48:7 › Profile — authenticated › renders profile page 

    Test timeout of 30000ms exceeded while running "beforeEach" hook.

      19 |
      20 | test.describe('Profile — authenticated', () => {
    > 21 |   test.beforeEach(async ({ page }) => {
         |        ^
      22 |     await setAuthToken(page);
      23 |     await mockAuthMe(page);
      24 |     await mockAuthRefresh(page);
        at /mnt/c/Users/aleja/Desktop/claude/Transcendence/front/e2e/profile.spec.ts:21:8

    Error: page.waitForResponse: Test timeout of 30000ms exceeded.
    =========================== logs ===========================
    waiting for response "**/auth/me"
    ============================================================

       at helpers.ts:112

      110 |  */
      111 | export async function bootAuthenticated(page: Page): Promise<void> {
    > 112 |   const authDone = page.waitForResponse('**/auth/me');
          |                         ^
      113 |   await page.goto('/');
      114 |   await authDone;
      115 | }
        at bootAuthenticated (/mnt/c/Users/aleja/Desktop/claude/Transcendence/front/e2e/helpers.ts:112:25)
        at /mnt/c/Users/aleja/Desktop/claude/Transcendence/front/e2e/profile.spec.ts:45:28

    Error Context: test-results/profile-Profile-—-authenticated-renders-profile-page-chromium/error-context.md

  4) [chromium] › e2e/tournaments.spec.ts:33:7 › Tournaments — authenticated › renders tournament page 

    Test timeout of 30000ms exceeded while running "beforeEach" hook.

      20 |
      21 | test.describe('Tournaments — authenticated', () => {
    > 22 |   test.beforeEach(async ({ page }) => {
         |        ^
      23 |     await setAuthToken(page);
      24 |     await mockAuthMe(page);
      25 |     await mockAuthRefresh(page);
        at /mnt/c/Users/aleja/Desktop/claude/Transcendence/front/e2e/tournaments.spec.ts:22:8

    Error: page.waitForResponse: Test timeout of 30000ms exceeded.
    =========================== logs ===========================
    waiting for response "**/auth/me"
    ============================================================

       at helpers.ts:112

      110 |  */
      111 | export async function bootAuthenticated(page: Page): Promise<void> {
    > 112 |   const authDone = page.waitForResponse('**/auth/me');
          |                         ^
      113 |   await page.goto('/');
      114 |   await authDone;
      115 | }
        at bootAuthenticated (/mnt/c/Users/aleja/Desktop/claude/Transcendence/front/e2e/helpers.ts:112:25)
        at /mnt/c/Users/aleja/Desktop/claude/Transcendence/front/e2e/tournaments.spec.ts:30:28

    Error Context: test-results/tournaments-Tournaments-—--0464f-ted-renders-tournament-page-chromium/error-context.md

  5) [chromium] › e2e/tournaments.spec.ts:39:7 › Tournaments — authenticated › shows empty state when no tournaments 

    Test timeout of 30000ms exceeded while running "beforeEach" hook.

      20 |
      21 | test.describe('Tournaments — authenticated', () => {
    > 22 |   test.beforeEach(async ({ page }) => {
         |        ^
      23 |     await setAuthToken(page);
      24 |     await mockAuthMe(page);
      25 |     await mockAuthRefresh(page);
        at /mnt/c/Users/aleja/Desktop/claude/Transcendence/front/e2e/tournaments.spec.ts:22:8

    Error: page.waitForResponse: Test timeout of 30000ms exceeded.
    =========================== logs ===========================
    waiting for response "**/auth/me"
    ============================================================

       at helpers.ts:112

      110 |  */
      111 | export async function bootAuthenticated(page: Page): Promise<void> {
    > 112 |   const authDone = page.waitForResponse('**/auth/me');
          |                         ^
      113 |   await page.goto('/');
      114 |   await authDone;
      115 | }
        at bootAuthenticated (/mnt/c/Users/aleja/Desktop/claude/Transcendence/front/e2e/helpers.ts:112:25)
        at /mnt/c/Users/aleja/Desktop/claude/Transcendence/front/e2e/tournaments.spec.ts:30:28

    Error Context: test-results/tournaments-Tournaments-—--51f64-y-state-when-no-tournaments-chromium/error-context.md

  6) [chromium] › e2e/tournaments.spec.ts:46:7 › Tournaments — authenticated › create tournament button is visible 

    Test timeout of 30000ms exceeded while running "beforeEach" hook.

      20 |
      21 | test.describe('Tournaments — authenticated', () => {
    > 22 |   test.beforeEach(async ({ page }) => {
         |        ^
      23 |     await setAuthToken(page);
      24 |     await mockAuthMe(page);
      25 |     await mockAuthRefresh(page);
        at /mnt/c/Users/aleja/Desktop/claude/Transcendence/front/e2e/tournaments.spec.ts:22:8

    Error: page.waitForResponse: Test timeout of 30000ms exceeded.
    =========================== logs ===========================
    waiting for response "**/auth/me"
    ============================================================

       at helpers.ts:112

      110 |  */
      111 | export async function bootAuthenticated(page: Page): Promise<void> {
    > 112 |   const authDone = page.waitForResponse('**/auth/me');
          |                         ^
      113 |   await page.goto('/');
      114 |   await authDone;
      115 | }
        at bootAuthenticated (/mnt/c/Users/aleja/Desktop/claude/Transcendence/front/e2e/helpers.ts:112:25)
        at /mnt/c/Users/aleja/Desktop/claude/Transcendence/front/e2e/tournaments.spec.ts:30:28

    Error Context: test-results/tournaments-Tournaments-—--c4a28-ournament-button-is-visible-chromium/error-context.md

  6 failed
    [chromium] › e2e/auth.spec.ts:41:7 › Auth — login › guest guard redirects authenticated user away from /login 
    [chromium] › e2e/auth.spec.ts:61:7 › Auth — register › guest guard redirects authenticated user away from /register 
    [chromium] › e2e/profile.spec.ts:48:7 › Profile — authenticated › renders profile page 
    [chromium] › e2e/tournaments.spec.ts:33:7 › Tournaments — authenticated › renders tournament page 
    [chromium] › e2e/tournaments.spec.ts:39:7 › Tournaments — authenticated › shows empty state when no tournaments 
    [chromium] › e2e/tournaments.spec.ts:46:7 › Tournaments — authenticated › create tournament button is visible 
  11 passed (36.5s)
