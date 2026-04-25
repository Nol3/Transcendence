import { RenderMode, ServerRoute } from '@angular/ssr';

export const serverRoutes: ServerRoute[] = [
  { path: 'game', renderMode: RenderMode.Client },
  { path: 'tournament', renderMode: RenderMode.Client },
  { path: 'profile', renderMode: RenderMode.Client },
  { path: '**', renderMode: RenderMode.Server },
];
