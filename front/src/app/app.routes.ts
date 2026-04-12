import { Routes } from '@angular/router';
import { Componente1 } from './componente1/componente1';
import { Componente2 } from './componente2/componente2';
import { Componente3 } from './componente3/componente3';

export const routes: Routes = [
  { path: '', component: Componente1 },
  { path: 'componente1', component: Componente1 },
  { path: 'componente2', component: Componente2 },
  { path: 'componente3', component: Componente3 },
];
