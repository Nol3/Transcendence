import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { App } from './app/app';
import { I18nService } from './app/i18n/i18n.service';
import { APP_INITIALIZER } from '@angular/core';

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
  providers: [...appConfig.providers, appInitializerProvider],
}).catch((err) => console.error(err));
