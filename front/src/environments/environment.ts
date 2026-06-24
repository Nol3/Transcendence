export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000/api',
  get wsUrl(): string {
    if (typeof window === 'undefined') return 'ws://localhost:8000/ws';
    const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
    return `${scheme}://${window.location.host}/ws`;
  },
  // Relative so the game is served same-origin (via nginx proxy → backend),
  // avoiding cross-origin CORS/COEP on index.wasm/.data.
  gameUrl: '/game-embed/',
  gameAssetsUrl: '/game-assets',
  googleClientId: '1067739742379-t0t8p1agm0eoej2l2tjklk80igc30t6k.apps.googleusercontent.com', // TODO: paste your Google OAuth Client ID here
};
