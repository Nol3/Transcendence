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
    path: 'game',
    loadComponent: () => import('./features/game/game-board/game-board').then((m) => m.GameBoard),
    canActivate: [authGuard],
  },
  {
    path: 'game-wrap',
    loadComponent: () => import('./features/game/embed-wrapper/embed-wrapper').then((m) => m.GameWrapComponent),
  },
  {
    path: 'tournament',
    loadComponent: () => import('./features/game/tournament/tournament').then((m) => m.Tournament),
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
