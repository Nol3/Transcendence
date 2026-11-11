import { Injectable, computed, signal } from '@angular/core';

import { BARAJA_POR_DEFECTO, CardDeck, DECKS } from '../shared/components/playing-card/decks';

/** Clave de `localStorage`. Lleva versión para poder cambiar el formato sin romper nada. */
const CLAVE = 'transcendence.baraja.v1';

/**
 * La baraja con la que se juega. Vive en un servicio y no en cada juego para que cambiarla en la
 * cabecera afecte a **todas** las mesas a la vez y se recuerde al volver.
 *
 * La baraja es solo arte: las reglas no cambian (la sota sigue siendo la carta 10 por dentro).
 */
@Injectable({ providedIn: 'root' })
export class Baraja {
  private readonly actual = signal<CardDeck>(this.leer());

  /** La baraja elegida, para leerla desde las plantillas. */
  readonly baraja = this.actual.asReadonly();

  /** Todas las disponibles, para pintar el selector. */
  readonly disponibles = computed(() =>
    (Object.keys(DECKS) as CardDeck[]).map((clave) => ({ clave, ...DECKS[clave] })),
  );

  /** Cambia la baraja y la recuerda. No recarga: `playing-card` recibe `deck` como input. */
  elegir(deck: CardDeck): void {
    if (deck === this.actual()) return;
    this.actual.set(deck);
    this.guardar(deck);
  }

  private leer(): CardDeck {
    try {
      const guardada = globalThis.localStorage?.getItem(CLAVE);
      if (guardada && guardada in DECKS) return guardada as CardDeck;
    } catch {
      // Navegación privada o almacenamiento lleno: se juega con la de por defecto.
    }
    return BARAJA_POR_DEFECTO;
  }

  private guardar(deck: CardDeck): void {
    try {
      globalThis.localStorage?.setItem(CLAVE, deck);
    } catch {
      // Si no se puede guardar, la elección vale para esta sesión y ya está.
    }
  }
}
