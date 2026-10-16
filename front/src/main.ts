import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { App } from './app/app';
import { I18nService } from './app/i18n/i18n.service';
import { APP_INITIALIZER, isDevMode } from '@angular/core';
import { provideServiceWorker } from '@angular/service-worker';

function initializeI18n(i18nService: I18nService) {
  return () => i18nService.init();
}

const appInitializerProvider = {
  provide: APP_INITIALIZER,
  useFactory: initializeI18n,
  deps: [I18nService],
  multi: true,
};

bootstrapApplication(App, {
  ...appConfig,
  providers: [...appConfig.providers, appInitializerProvider, provideServiceWorker('ngsw-worker.js', {
            enabled: !isDevMode(),
            registrationStrategy: 'registerWhenStable:30000'
          })],
}).catch((err) => console.error(err));
