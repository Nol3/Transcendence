import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';

import {
  GAME_CATALOG,
  GameEntry,
  GameMode,
  UPCOMING_GAMES,
  modeKey,
} from '../../../core/games/game-catalog';
import { BadgeComponent } from '../../../shared/components/badge/badge';
import { ButtonComponent } from '../../../shared/components/button/button';
import { PixelTitleComponent } from '../../../shared/components/pixel-title/pixel-title';
import { TranslatePipe } from '../../../i18n';

/**
 * Apartado «Juegos»: la parrilla con todo lo que se puede jugar.
 *
 * No tiene lógica propia: lo que enseña sale del catálogo (`core/games/game-catalog.ts`),
 * así que un juego nuevo aparece aquí en cuanto se declara, sin tocar esta pantalla.
 */
@Component({
  selector: 'app-games-hub',
  imports: [BadgeComponent, ButtonComponent, PixelTitleComponent, RouterLink, TranslatePipe],
  templateUrl: './games-hub.html',
  styleUrl: './games-hub.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GamesHub {
  readonly games = GAME_CATALOG;
  readonly upcoming = UPCOMING_GAMES;

  readonly modeKey = modeKey;

  /** Distintivo del modo: en local no hace falta prometer nada, en online sí. */
  badgeFor(mode: GameMode): 'default' | 'info' | 'success' {
    if (mode === 'online') return 'success';
    if (mode === 'bots') return 'info';
    return 'default';
  }

  trackById(_indice: number, juego: GameEntry): string {
    return juego.id;
  }
}
