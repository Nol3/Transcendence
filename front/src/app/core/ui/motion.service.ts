import { DOCUMENT, isPlatformBrowser } from '@angular/common';
import { Injectable, PLATFORM_ID, effect, inject, signal } from '@angular/core';

const CLAVE = 'juegos_movimiento_reducido';

/**
 * Movimiento reducido, a mano además de por sistema.
 *
 * `prefers-reduced-motion` cubre a quien lo pide en el SO, pero no a quien quiere jugar
 * sin rebotes en un dispositivo que no lo tiene configurado. Balatro pone esta opción en
 * primer nivel; aquí se guarda por dispositivo (localStorage), porque es una preferencia
 * de cómo se ve la app, no una propiedad de la cuenta.
 *
 * Aplica la clase `reduce-motion` a `<html>`; el CSS global se encarga del resto.
 */
@Injectable({ providedIn: 'root' })
export class MotionService {
  private readonly doc = inject(DOCUMENT);
  private readonly platform = inject(PLATFORM_ID);

  private readonly _reduce = signal(this.inicial());
  readonly reduce = this._reduce.asReadonly();

  constructor() {
    effect(() => this.aplicar(this._reduce()));
  }

  /** Cambia la preferencia y la recuerda. Devuelve el valor nuevo. */
  alternar(): boolean {
    const valor = !this._reduce();
    this._reduce.set(valor);
    try {
      this.doc.defaultView?.localStorage.setItem(CLAVE, valor ? '1' : '0');
    } catch {
      // Sin localStorage (modo privado) funciona igual; solo no se recuerda.
    }
    return valor;
  }

  private inicial(): boolean {
    if (!isPlatformBrowser(this.platform)) return false;
    try {
      return this.doc.defaultView?.localStorage.getItem(CLAVE) === '1';
    } catch {
      return false;
    }
  }

  private aplicar(valor: boolean): void {
    if (!isPlatformBrowser(this.platform)) return;
    this.doc.documentElement.classList.toggle('reduce-motion', valor);
  }
}
