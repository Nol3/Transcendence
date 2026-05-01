# Error Audit — May 1, 2026

## Summary
7 errors/warnings detected on login and game start. **4 pre-existing**, **2 expected after postMessage refactor**, **1 fixable (Google button)**.

---

## Errors by Category

### ✅ Pre-Existing (Out of Scope)
| Error | Cause | Status |
|-------|-------|--------|
| `Unable to add filesystem: <illegal path>` | Emscripten WASM preload issue | Harmless, game loads anyway |
| `mergeInto is not defined` @ index.js:1 | Emscripten post-js script ordering | Pre-dates username feature |
| `PendingTasks keeping application unstable` | Angular router/zone.js race condition | Pre-dates current session |

---

### 🔄 Expected (After postMessage Refactor)
| Error | Reason |
|-------|--------|
| `GET /api/auth/me/ 401 Unauthorized` | Intentionally removed fetch; now using postMessage from Angular parent instead. Falls back to "Jugador 1" if no postMessage received. |
| `[GSI_LOGGER]: The given origin is not allowed for client ID` | Google OAuth client ID `1067739742379-...` not whitelisted for `localhost:4200`. Env config issue, not code. |

---

### 🟡 Fixable (In Scope)

#### 1. Google Sign-In Button Width Invalid
**Location:** `auth.service.ts` line 206 (`renderGoogleButton()`)  
**Error:** `[GSI_LOGGER]: Provided button width is invalid: 100%`  
**Cause:** Passing `width: "100%"` to Google Identity Services button renderer; must be pixels.  
**Fix:** Change to `width: 300` (or detect parent width in pixels).

#### 2. Iframe Sandbox Too Permissive  
**Location:** `game-board.html` iframe  
**Warning:** `An iframe which has both allow-scripts and allow-same-origin for its sandbox attribute can escape its sandboxing`  
**Current:** `sandbox="allow-scripts allow-same-origin allow-pointer-lock allow-popups"`  
**Fix:** Remove `allow-same-origin` (postMessage works cross-origin); game doesn't need same-origin access.

---

## Impact Assessment

| Issue | Severity | UX Impact | User-Facing |
|-------|----------|-----------|-------------|
| Filesystem path | Low | None | No |
| mergeInto | Low | None | No |
| PendingTasks | Medium | Slight delay on route change | Slightly noticeable |
| 401 /api/auth/me | **None** | Username via postMessage works as intended | Transparent |
| Google OAuth origin | Medium | Google button doesn't render | Yes (workaround: manual email/password) |
| Google button width | Low | Button may overflow | Slightly |
| Iframe sandbox | Low | Security best practice only | No |

---

## Recommended Fixes (Prioritized)

1. **MUST:** Remove `allow-same-origin` from iframe sandbox (security)
2. **SHOULD:** Fix Google button width to pixels (UX)
3. **INFO:** Document that `401 /api/auth/me` is intentional (logging clarity)
4. **OPTIONAL:** Investigate PendingTasks on router (preexisting, low priority)
5. **CONFIG:** Whitelist `localhost:4200` in Google OAuth client (outside code)

---

## Updates — After Initial Setup

### ✅ Fixed
- `STATICFILES_DIRS` warning: Removed unused `static/` directory reference from Django settings.py (line 127)

### 🔴 New: Google OAuth Origin Blocked
**Location:** Chrome console on login page  
**Error:** `The given origin is not allowed for the given client ID`  
**Cause:** Google OAuth client ID `1067739742379-...` configured in Google Cloud Console does **not** include `localhost:4200` in authorized origins.  
**Fix (CONFIG ONLY):**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Find project > APIs & Services > Credentials
3. Edit the OAuth 2.0 Client ID (`1067739742379-...`)
4. Add authorized origin: `http://localhost:4200`
5. Save

**Impact:** Without this, Google Sign-In button won't work. Users must use email/password login.

---

### 🔴 New: Cross-Origin-Opener-Policy Blocks postMessage
**Location:** Chrome console on login redirect  
**Error:** `Cross-Origin-Opener-Policy policy would block the window.postMessage call`  
**Cause:** Django sets `Cross-Origin-Opener-Policy: same-origin` on `/game/` (COOP header). Google's popup tries to postMessage back to Angular (different origin :4200 vs :8000), but COOP blocks it.  
**Current:** login happens at `:4200` (Angular), popup redirects to `:8000` (Django game view), COOP header blocks popup→parent messaging.  
**Fix:** Relax COOP policy for `/game/` route if Google Sign-In redirect targets it. OR redirect Google callback to Angular login callback handler instead of game view.

**Note:** This is a security-by-design issue (COOP prevents clickjacking). Low priority if email/password login works.

---

## Final Status

| Issue | Fix | Priority |
|-------|-----|----------|
| Django static warning | ✅ Removed STATICFILES_DIRS | Done |
| Google OAuth not whitelisted | 🔴 Config only (Google Cloud Console) | **Blocker for Google Sign-In** |
| COOP blocks postMessage | 🟡 Arch decision (relax header vs change redirect) | Low (workaround: email login) |
| Unable to add filesystem | ✅ Pre-existing, harmless | Ignore |
| mergeInto not defined | ✅ Pre-existing Emscripten | Ignore |
| Google button width | ✅ Fixed (100% → 300px) | Done |
| Iframe sandbox | ✅ Removed allow-same-origin | Done |

