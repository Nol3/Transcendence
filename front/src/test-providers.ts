import { provideZonelessChangeDetection } from '@angular/core';

/**
 * Providers comunes a todos los tests unitarios.
 *
 * La aplicación es **zoneless** (Angular 20, `provideZonelessChangeDetection`), así
 * que el TestBed necesita lo mismo: sin esto, los tests fallan con
 * «NG0908: In this configuration Angular requires Zone.js».
 */
export default [provideZonelessChangeDetection()];
