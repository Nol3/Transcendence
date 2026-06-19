export const environment = {
  production: true,
  apiUrl: '/api',
  // Derived from the current origin so WS works wherever the app is served
  // (e.g. wss://localhost:8443/ws behind nginx). Guarded for SSR (no window).
  get wsUrl(): string {
    if (typeof window === 'undefined') return '/ws';
    const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
    return `${scheme}://${window.location.host}/ws`;
  },
  gameUrl: '/game-embed/',
  gameAssetsUrl: '/game-assets',
  // OAuth client IDs are public (sent to the browser) — safe to ship. The
  // client *secret* must never be here; the backend only verifies the ID token.
  googleClientId: '1067739742379-t0t8p1agm0eoej2l2tjklk80igc30t6k.apps.googleusercontent.com',
};
