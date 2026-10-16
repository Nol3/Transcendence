/**
 * Los efectos de sonido de las mesas.
 *
 * Los ficheros están en `public/game-assets/audio/` y son **sintetizados** para el proyecto (tonos
 * retro cortos, que pegan con la fuente pixelada), así que no hay que acreditar a nadie.
 *
 * Todo va envuelto: si el navegador bloquea el audio hasta que el usuario toca algo, o si el
 * fichero no está, la partida sigue igual. Un sonido no puede tumbar una mesa de cartas.
 */

import { Injectable } from '@angular/core';

const RUTA = '/game-assets/audio';
const CLAVE_SILENCIO = 'juegos_sin_sonido';

/** Cada efecto, con su volumen: no todos los momentos pesan lo mismo. */
const EFECTOS = {
  repartir: { archivo: 'card_deal.wav', volumen: 0.5 },
  tocar: { archivo: 'card_select.wav', volumen: 0.35 },
  soltar: { archivo: 'card_flip.wav', volumen: 0.5 },
  boton: { archivo: 'button_click.wav', volumen: 0.3 },
  pasar: { archivo: 'discard.wav', volumen: 0.4 },
  baza: { archivo: 'trick_win.wav', volumen: 0.4 },
  finDeRonda: { archivo: 'win_round.wav', volumen: 0.45 },
  derrota: { archivo: 'lose_round.wav', volumen: 0.4 },
  victoria: { archivo: 'win_game.wav', volumen: 0.5 },
  error: { archivo: 'error.wav', volumen: 0.35 },
  piedra: { archivo: 'chip.wav', volumen: 0.4 },
  barrido: { archivo: 'whoosh.wav', volumen: 0.4 },
  tic: { archivo: 'tick.wav', volumen: 0.25 },
} as const;

export type Efecto = keyof typeof EFECTOS;

/**
 * Reproductor de efectos de una mesa.
 *
 * Cada mesa tiene el suyo, para que silenciar una no silencie las demás, pero el silencio se
 * **recuerda** entre sesiones: si alguien apaga el sonido, no quiere volver a apagarlo cada vez.
 */
@Injectable({ providedIn: 'root' })
export class GameSound {
  private activo = !this.silencioGuardado();
  private readonly cache = new Map<Efecto, HTMLAudioElement>();

  /** ¿Está sonando? Para pintar el botón. */
  get encendido(): boolean {
    return this.activo;
  }

  activar(valor: boolean): void {
    this.activo = valor;
    try {
      window.localStorage.setItem(CLAVE_SILENCIO, valor ? '0' : '1');
    } catch {
      // Sin localStorage (modo privado, por ejemplo) el sonido funciona igual, solo no se recuerda.
    }
  }

  alternar(): boolean {
    this.activar(!this.activo);
    return this.activo;
  }

  // ── Los momentos de una partida ───────────────────────────────────────────

  /** Se reparten cartas. */
  repartir(): void { this.suena('repartir'); }
  /** Se elige una carta de la mano. */
  tocar(): void { this.suena('tocar'); }
  /** Se juega una carta. */
  soltar(): void { this.suena('soltar'); }
  /** Se pulsa un botón cualquiera. */
  boton(): void { this.suena('boton'); }
  /** Algo no se puede hacer. */
  error(): void { this.suena('error'); }
  /** Se gana una baza. */
  baza(): void { this.suena('baza'); }
  /** Se gana la mano o el juego. */
  finDeRonda(): void { this.suena('finDeRonda'); }
  /** Se pierde. */
  derrota(): void { this.suena('derrota'); }
  /** Se gana la partida entera. */
  victoria(): void { this.suena('victoria'); }
  /** Se paga: piedras del mus. */
  piedra(): void { this.suena('piedra'); }
  /** Algo se lleva o cambia de sitio. */
  barrido(): void { this.suena('barrido'); }
  /** Un tic, para el turno. */
  tic(): void { this.suena('tic'); }

  /** Compatibilidad con el nombre que usaban las mesas antes. */
  pasar(): void { this.suena('pasar'); }

  private suena(clave: Efecto): void {
    if (!this.activo || typeof Audio === 'undefined') return;
    try {
      let audio = this.cache.get(clave);
      if (!audio) {
        audio = new Audio(`${RUTA}/${EFECTOS[clave].archivo}`);
        audio.volume = EFECTOS[clave].volumen;
        audio.preload = 'auto';
        this.cache.set(clave, audio);
      }
      audio.currentTime = 0;
      void audio.play().catch(() => undefined);
    } catch {
      // Sin sonido, pero sin romper nada.
    }
  }

  private silencioGuardado(): boolean {
    try {
      return window.localStorage.getItem(CLAVE_SILENCIO) === '1';
    } catch {
      return false;
    }
  }
}
