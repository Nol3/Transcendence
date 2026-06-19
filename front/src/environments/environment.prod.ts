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
  googleClientId: '', // TODO: paste your Google OAuth Client ID here
};
