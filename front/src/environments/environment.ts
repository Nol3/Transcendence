export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000/api',
  wsUrl: 'ws://localhost:8000/ws',
  // Relative so the game is served same-origin (via nginx proxy → backend),
  // avoiding cross-origin CORS/COEP on index.wasm/.data.
  gameUrl: '/game/',
  gameAssetsUrl: '/game-assets',
  googleClientId: '1067739742379-t0t8p1agm0eoej2l2tjklk80igc30t6k.apps.googleusercontent.com', // TODO: paste your Google OAuth Client ID here
};
