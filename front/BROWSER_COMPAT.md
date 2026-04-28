# Browser Compatibility Report

**Module:** Browser Compatibility (Minor — 1 pt)
**Tested:** 2026-04-28
**Tool:** Playwright automated E2E (17 tests × 3 browsers = 51 total)

## Test Results

| Browser | Version | Tests | Result |
|---------|---------|-------|--------|
| Chromium (Chrome) | Desktop Chrome | 17/17 | ✅ PASS |
| Firefox | Desktop Firefox | 17/17 | ✅ PASS |
| Microsoft Edge | Desktop Edge | 17/17 | ✅ PASS |

All 51 tests passed in ~44s.

## Coverage per Browser

### Auth flows
| Test | Chrome | Firefox | Edge |
|------|--------|---------|------|
| Login form renders | ✅ | ✅ | ✅ |
| Validation errors on empty submit | ✅ | ✅ | ✅ |
| Successful login → redirect home | ✅ | ✅ | ✅ |
| Guest guard: redirect authenticated user away from /login | ✅ | ✅ | ✅ |
| Register form renders | ✅ | ✅ | ✅ |
| Guest guard: redirect authenticated user away from /register | ✅ | ✅ | ✅ |

### Home page
| Test | Chrome | Firefox | Edge |
|------|--------|---------|------|
| Hero section renders | ✅ | ✅ | ✅ |
| Leaderboard card renders | ✅ | ✅ | ✅ |
| Leaderboard shows rows after loading | ✅ | ✅ | ✅ |
| Leaderboard shows player names | ✅ | ✅ | ✅ |
| Unauthenticated: login button visible in hero | ✅ | ✅ | ✅ |

### Profile page
| Test | Chrome | Firefox | Edge |
|------|--------|---------|------|
| Auth guard: unauthenticated /profile → /login | ✅ | ✅ | ✅ |
| Authenticated: profile page renders | ✅ | ✅ | ✅ |

### Tournaments page
| Test | Chrome | Firefox | Edge |
|------|--------|---------|------|
| Auth guard: unauthenticated /tournament → /login | ✅ | ✅ | ✅ |
| Authenticated: tournament page renders | ✅ | ✅ | ✅ |
| Shows empty state when no tournaments | ✅ | ✅ | ✅ |
| Create tournament button is visible | ✅ | ✅ | ✅ |

## Known Limitations

### Safari / iOS
Not testable from Windows environment. Safari requires macOS/iOS hardware.
Angular 21 + CSS custom properties are fully supported in Safari 15.4+. No custom polyfills needed.

### IE11
Not supported. Angular 21 drops IE11 support by design. Evaluators should use Chrome, Firefox, or Edge.

## Technical Notes

- **CSS custom properties** (`--color-*`, `--font-*` tokens): supported in all three browsers without fallbacks.
- **Angular Signals**: JS feature with full Chromium/Firefox/Edge support.
- **EventSource (SSE)**: supported natively in Chromium, Firefox, Edge. Not available in IE11 (irrelevant).
- **WebCrypto / JWT**: available in all modern browsers under HTTPS (localhost included for dev).
- **localStorage**: behaves identically across all three browsers for auth token storage.
- **CSS animations** (scanlines, glows, neon transitions): render consistently — no browser-specific keyframe issues found.
- **WASM game embed** (`<iframe>` to Django `/game/`): cross-origin headers (`COOP/COEP`) required. Same behavior across browsers.

## How to Reproduce

```bash
cd front/
npm install
npx playwright install chromium firefox msedge
npx playwright test
```
