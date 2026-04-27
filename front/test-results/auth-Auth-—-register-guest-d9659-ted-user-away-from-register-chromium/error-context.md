# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: auth.spec.ts >> Auth — register >> guest guard redirects authenticated user away from /register
- Location: e2e/auth.spec.ts:61:7

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: page.waitForResponse: Test timeout of 30000ms exceeded.
=========================== logs ===========================
waiting for response "**/auth/me"
============================================================
```

# Page snapshot

```yaml
- generic [ref=e2]:
  - banner [ref=e4]:
    - generic [ref=e5]:
      - link "TRANS CENDENCE" [ref=e6] [cursor=pointer]:
        - /url: /
        - generic [ref=e7]: TRANS
        - generic [ref=e8]: CENDENCE
      - navigation "Main navigation" [ref=e9]:
        - link "Home" [ref=e10] [cursor=pointer]:
          - /url: /
        - link "Play" [ref=e11] [cursor=pointer]:
          - /url: /game
        - link "Tournament" [ref=e12] [cursor=pointer]:
          - /url: /tournament
      - generic [ref=e13]:
        - button "🇬🇧 EN ▼" [ref=e16] [cursor=pointer]:
          - generic [ref=e17]: 🇬🇧
          - generic [ref=e18]: EN
          - generic [ref=e19]: ▼
        - link "Login" [ref=e20] [cursor=pointer]:
          - /url: /login
        - link "Register" [ref=e21] [cursor=pointer]:
          - /url: /register
  - main [ref=e22]:
    - generic [ref=e24]:
      - generic [ref=e28]:
        - generic [ref=e29]: 11:58:51
        - generic:
          - heading [level=1]
        - paragraph [ref=e30]: Insert coin to play
        - paragraph [ref=e31]: The ultimate card battle experience
        - generic [ref=e32]:
          - button "Insert coin to play" [ref=e34] [cursor=pointer]:
            - generic [ref=e35]: Insert coin to play
          - button "Login" [ref=e37] [cursor=pointer]:
            - generic [ref=e38]: Login
        - generic [ref=e41]: Ready
      - generic [ref=e44]:
        - generic [ref=e45]:
          - generic [ref=e46]: "150"
          - generic [ref=e47]: Total Players
        - generic [ref=e48]:
          - generic [ref=e49]: 1,200
          - generic [ref=e50]: Games Played
        - generic [ref=e51]:
          - generic [ref=e52]: "52"
          - generic [ref=e53]: CARDS
        - generic [ref=e54]:
          - generic [ref=e55]: "3"
          - generic [ref=e56]: Tournament
      - generic [ref=e58]:
        - generic [ref=e60]:
          - heading "Leaderboard" [level=3] [ref=e62]
          - generic [ref=e64]:
            - generic [ref=e65]:
              - generic [ref=e66]:
                - generic [ref=e69]: ▲
                - generic [ref=e70]: player1
                - generic [ref=e71]:
                  - generic [ref=e72]: 10W
                  - generic [ref=e73]: 0L
                  - generic [ref=e74]: 100%
              - generic [ref=e75]:
                - generic [ref=e78]: ●
                - generic [ref=e79]: player2
                - generic [ref=e80]:
                  - generic [ref=e81]: 9W
                  - generic [ref=e82]: 1L
                  - generic [ref=e83]: 90%
              - generic [ref=e84]:
                - generic [ref=e87]: ■
                - generic [ref=e88]: player3
                - generic [ref=e89]:
                  - generic [ref=e90]: 8W
                  - generic [ref=e91]: 2L
                  - generic [ref=e92]: 80%
            - link "Rankings →" [ref=e94] [cursor=pointer]:
              - /url: /tournament
        - generic [ref=e95]:
          - generic [ref=e97]:
            - heading "How to Play" [level=3] [ref=e99]
            - list [ref=e102]:
              - listitem [ref=e103]:
                - generic [ref=e104]: "01"
                - generic [ref=e105]: Register
              - listitem [ref=e106]:
                - generic [ref=e107]: "02"
                - generic [ref=e108]: Tournament
              - listitem [ref=e109]:
                - generic [ref=e110]: "03"
                - generic [ref=e111]: Card Game
              - listitem [ref=e112]:
                - generic [ref=e113]: "04"
                - generic [ref=e114]: Leaderboard
          - generic [ref=e115]:
            - paragraph [ref=e116]: Card Game
            - paragraph [ref=e117]: Challenge opponents in epic card battles. Build your deck, outsmart your rival, and climb the ranks to become the ultimate champion.
            - button "Login" [ref=e119] [cursor=pointer]:
              - generic [ref=e120]: Login
  - contentinfo [ref=e122]:
    - generic [ref=e123]:
      - generic [ref=e124]:
        - text: TRANSCENDENCE
        - paragraph [ref=e125]: The ultimate card battle experience
      - navigation "Footer navigation" [ref=e126]:
        - generic [ref=e127]:
          - heading "Game" [level=4] [ref=e128]
          - link "Home" [ref=e129] [cursor=pointer]:
            - /url: /
          - link "Play" [ref=e130] [cursor=pointer]:
            - /url: /game
          - link "Tournament" [ref=e131] [cursor=pointer]:
            - /url: /tournament
        - generic [ref=e132]:
          - heading "Account" [level=4] [ref=e133]
          - link "Login" [ref=e134] [cursor=pointer]:
            - /url: /login
          - link "Register" [ref=e135] [cursor=pointer]:
            - /url: /register
          - link "Profile" [ref=e136] [cursor=pointer]:
            - /url: /profile
        - generic [ref=e137]:
          - heading "Legal" [level=4] [ref=e138]
          - link "Privacy Policy" [ref=e139] [cursor=pointer]:
            - /url: /privacy
          - link "Terms of Service" [ref=e140] [cursor=pointer]:
            - /url: /terms
      - generic [ref=e141]:
        - paragraph [ref=e142]: © 2026 Transcendence. All rights reserved.
        - generic [ref=e143]:
          - link "GitHub" [ref=e144] [cursor=pointer]:
            - /url: "#"
            - img [ref=e145]
          - link "Discord" [ref=e147] [cursor=pointer]:
            - /url: "#"
            - img [ref=e148]
  - generic:
    - generic "Notifications"
```

# Test source

```ts
  12  | 
  13  | const MOCK_TOKENS = {
  14  |   accessToken: 'mock-access-token',
  15  |   refreshToken: 'mock-refresh-token',
  16  | };
  17  | 
  18  | export async function mockAuthMe(page: Page) {
  19  |   await page.route('**/auth/me', (route) =>
  20  |     route.fulfill({
  21  |       status: 200,
  22  |       contentType: 'application/json',
  23  |       body: JSON.stringify({ data: { user: MOCK_USER }, error: null }),
  24  |     }),
  25  |   );
  26  | }
  27  | 
  28  | export async function mockAuthLogin(page: Page) {
  29  |   await page.route('**/auth/login', (route) =>
  30  |     route.fulfill({
  31  |       status: 200,
  32  |       contentType: 'application/json',
  33  |       body: JSON.stringify({ data: { user: MOCK_USER, tokens: MOCK_TOKENS }, error: null }),
  34  |     }),
  35  |   );
  36  | }
  37  | 
  38  | export async function mockAuthRefresh(page: Page) {
  39  |   // Prevent the auth interceptor's 401→refresh→logout cascade by returning valid tokens
  40  |   await page.route('**/auth/refresh', (route) =>
  41  |     route.fulfill({
  42  |       status: 200,
  43  |       contentType: 'application/json',
  44  |       body: JSON.stringify({ data: { tokens: MOCK_TOKENS }, error: null }),
  45  |     }),
  46  |   );
  47  | }
  48  | 
  49  | export async function mockAuthLogout(page: Page) {
  50  |   await page.route('**/auth/logout', (route) =>
  51  |     route.fulfill({ status: 200, contentType: 'application/json', body: '{}' }),
  52  |   );
  53  | }
  54  | 
  55  | export async function mockLeaderboard(page: Page) {
  56  |   const entries = Array.from({ length: 3 }, (_, i) => ({
  57  |     rank: i + 1,
  58  |     user: { id: i + 1, username: `player${i + 1}`, avatar: null },
  59  |     wins: 10 - i,
  60  |     losses: i,
  61  |     winRate: Math.round(((10 - i) / 10) * 100),
  62  |     totalGames: 10,
  63  |   }));
  64  |   await page.route('**/leaderboard*', (route) =>
  65  |     route.fulfill({
  66  |       status: 200,
  67  |       contentType: 'application/json',
  68  |       body: JSON.stringify({
  69  |         data: entries,
  70  |         meta: { page: 1, limit: 10, total: 3, totalPages: 1 },
  71  |         error: null,
  72  |       }),
  73  |     }),
  74  |   );
  75  | }
  76  | 
  77  | export async function mockTournaments(page: Page) {
  78  |   // TournamentService uses HttpClient directly (not ApiService), expects a plain array
  79  |   await page.route(/\/tournament/, (route) =>
  80  |     route.fulfill({
  81  |       status: 200,
  82  |       contentType: 'application/json',
  83  |       body: JSON.stringify([]),
  84  |     }),
  85  |   );
  86  | }
  87  | 
  88  | export async function setAuthToken(page: Page) {
  89  |   await page.addInitScript(() => {
  90  |     localStorage.setItem('access_token', 'mock-access-token');
  91  |     localStorage.setItem('refresh_token', 'mock-refresh-token');
  92  |   });
  93  | }
  94  | 
  95  | /**
  96  |  * Trigger Angular SPA navigation without a full page reload.
  97  |  * Use after auth state is established (page loaded at '/' + /auth/me resolved).
  98  |  * This avoids the race condition between initAuth() and synchronous guards.
  99  |  */
  100 | export async function spaNavigate(page: Page, path: string): Promise<void> {
  101 |   await page.evaluate((p) => {
  102 |     window.history.pushState({}, '', p);
  103 |     window.dispatchEvent(new PopStateEvent('popstate', { state: null }));
  104 |   }, path);
  105 | }
  106 | 
  107 | /**
  108 |  * Boot app at the unguarded home page with auth fully established.
  109 |  * waitForResponse MUST be created before page.goto() to avoid missing the response.
  110 |  */
  111 | export async function bootAuthenticated(page: Page): Promise<void> {
> 112 |   const authDone = page.waitForResponse('**/auth/me');
      |                         ^ Error: page.waitForResponse: Test timeout of 30000ms exceeded.
  113 |   await page.goto('/');
  114 |   await authDone;
  115 | }
  116 | 
```