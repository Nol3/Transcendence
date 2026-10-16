import { Routes } from '@angular/router';
import { authGuard, guestGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () => import('./features/home/home').then((m) => m.Home),
  },
  {
    path: 'login',
    loadComponent: () => import('./features/auth/login/login').then((m) => m.Login),
    canActivate: [guestGuard],
  },
  {
    path: 'register',
    loadComponent: () => import('./features/auth/register/register').then((m) => m.Register),
    canActivate: [guestGuard],
  },
  {
    // Apartado «Juegos»: la parrilla con todo lo que se puede jugar. Lo que sale ahí
    // se declara en `core/games/game-catalog.ts`, no en esta pantalla.
    path: 'games',
    loadComponent: () => import('./features/games/games-hub/games-hub').then((m) => m.GamesHub),
    canActivate: [authGuard],
  },
  {
    path: 'game',
    loadComponent: () => import('./features/game/game-board/game-board').then((m) => m.GameBoard),
    canActivate: [authGuard],
  },
  {
    path: 'culo',
    loadComponent: () => import('./features/games/culo/culo').then((m) => m.Culo),
    canActivate: [authGuard],
  },
  {
    path: 'brisca',
    loadComponent: () => import('./features/games/brisca/brisca').then((m) => m.Brisca),
    canActivate: [authGuard],
  },
  {
    path: 'tute',
    loadComponent: () => import('./features/games/tute/tute').then((m) => m.Tute),
    canActivate: [authGuard],
  },
  {
    path: 'mus',
    loadComponent: () => import('./features/games/mus/mus').then((m) => m.Mus),
    canActivate: [authGuard],
  },
  {
    path: 'mentiroso',
    loadComponent: () => import('./features/games/mentiroso/mentiroso').then((m) => m.Mentiroso),
    canActivate: [authGuard],
  },
  {
    path: 'poker',
    loadComponent: () => import('./features/poker/poker').then((m) => m.Poker),
    canActivate: [authGuard],
  },
  {
    path: 'poker/history',
    loadComponent: () =>
      import('./features/poker/history/history').then((m) => m.PokerHistory),
    canActivate: [authGuard],
  },
  {
    path: 'tournament',
    loadComponent: () => import('./features/game/tournament/tournament').then((m) => m.Tournament),
    canActivate: [authGuard],
  },
  {
    path: 'tournament/:id',
    loadComponent: () => import('./features/game/tournament/tournament').then((m) => m.Tournament),
    canActivate: [authGuard],
  },
  {
    path: 'chat',
    loadComponent: () => import('./features/chat/chat').then((m) => m.Chat),
    canActivate: [authGuard],
  },
  {
    path: 'profile',
    loadComponent: () => import('./features/profile/profile').then((m) => m.Profile),
    canActivate: [authGuard],
  },
  {
    path: 'privacy',
    loadComponent: () => import('./features/legal/privacy/privacy').then((m) => m.PrivacyComponent),
  },
  {
    path: 'terms',
    loadComponent: () => import('./features/legal/terms/terms').then((m) => m.TermsComponent),
  },
  {
    path: '**',
    redirectTo: '',
  },
];
