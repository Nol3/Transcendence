export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000/api',
  // En desarrollo se apunta directamente al backend (como apiUrl); el dev-server
  // de Angular no proxya /ws. En producción se usa la ruta relativa, que nginx
  // reenvía al backend con el handshake de Upgrade.
  get wsUrl(): string {
    if (typeof window === 'undefined') return 'ws://localhost:8000/ws';
    const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
    return `${scheme}://localhost:8000/ws`;
  },
  // Relative so the game is served same-origin (via nginx proxy → backend),
  // avoiding cross-origin CORS/COEP on index.wasm/.data.
  gameUrl: '/game-embed/',
  gameAssetsUrl: '/game-assets',
  googleClientId: '1067739742379-t0t8p1agm0eoej2l2tjklk80igc30t6k.apps.googleusercontent.com', // TODO: paste your Google OAuth Client ID here
};
