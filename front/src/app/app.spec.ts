import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';

import { App } from './app';
import { routes } from './app.routes';

describe('App (armazón de la aplicación)', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [App],
      // La cabecera y el pie usan servicios que hablan con la API y con el router.
      providers: [provideRouter(routes), provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
  });

  it('se crea', () => {
    const fixture = TestBed.createComponent(App);
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('pinta la cabecera, el pie y el contenedor de avisos', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const html = fixture.nativeElement as HTMLElement;

    expect(html.querySelector('app-header')).toBeTruthy();
    expect(html.querySelector('app-footer')).toBeTruthy();
    expect(html.querySelector('app-toast')).toBeTruthy();
    // El contenido de cada ruta entra por el outlet del router.
    expect(html.querySelector('router-outlet')).toBeTruthy();
  });
});
