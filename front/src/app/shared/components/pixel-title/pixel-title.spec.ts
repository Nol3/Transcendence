import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';

import { PixelTitleComponent } from './pixel-title';

@Component({
  standalone: true,
  imports: [PixelTitleComponent],
  template: `
    <app-pixel-title [level]="1" color="cyan">Título uno</app-pixel-title>
    <app-pixel-title [level]="2" color="yellow">Título dos</app-pixel-title>
    <app-pixel-title [level]="3" color="green">Título tres</app-pixel-title>
  `,
})
class HostComponent {}

/**
 * El título se proyectaba con un `<ng-content>` dentro de cada `@case` del
 * `@switch`. Angular solo conserva una proyección, así que los headings salían
 * vacíos (la página no tenía título visible). Esta prueba lo impide.
 */
describe('PixelTitle', () => {
  it('pinta el contenido en el heading que corresponde a cada nivel', async () => {
    await TestBed.configureTestingModule({ imports: [HostComponent] }).compileComponents();
    const fixture = TestBed.createComponent(HostComponent);
    await fixture.whenStable();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('h1')?.textContent?.trim()).toBe('Título uno');
    expect(el.querySelector('h2')?.textContent?.trim()).toBe('Título dos');
    expect(el.querySelector('h3')?.textContent?.trim()).toBe('Título tres');
  });
});
