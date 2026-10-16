import { ApplicationConfig, isDevMode, provideBrowserGlobalErrorListeners, provideZonelessChangeDetection } from '@angular/core';
import { provideRouter, withComponentInputBinding } from '@angular/router';
import { provideHttpClient, withFetch, withInterceptors } from '@angular/common/http';
import { provideClientHydration, withEventReplay } from '@angular/platform-browser';
import { provideServiceWorker } from '@angular/service-worker';

import { routes } from './app.routes';
import { authInterceptor } from './core/interceptors/auth.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideZonelessChangeDetection(),
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes, withComponentInputBinding()),
    provideHttpClient(withFetch(), withInterceptors([authInterceptor])),
    provideClientHydration(withEventReplay()),
    // PWA (roadmap 7.4): instalable y con la app en caché. En desarrollo se deja
    // apagado a propósito: un service worker sirviendo código viejo complica el día a
    // día (y los e2e corren contra el servidor de desarrollo).
    provideServiceWorker('ngsw-worker.js', {
      enabled: !isDevMode(),
      // La cadena es la forma que acepta Angular 20 (no existe `registerWhenStable`).
      registrationStrategy: 'registerWhenStable:30000',
    }),
  ],
};
