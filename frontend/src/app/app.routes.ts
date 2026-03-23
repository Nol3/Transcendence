import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', redirectTo: '/home', pathMatch: 'full' },
  // Load modules lazily
  // { path: 'home', loadComponent: () => import('./modules/..') },
];
