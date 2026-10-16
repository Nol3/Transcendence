import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import {
  PokerHandReplay,
  PokerHandView,
  PokerHistoryService,
  PokerMatchSummary,
} from '../../../core/services/poker-history.service';
import { cardParts } from '../../../core/services/poker.service';
import { BadgeComponent } from '../../../shared/components/badge/badge';
import { ButtonComponent } from '../../../shared/components/button/button';
import { CardComponent } from '../../../shared/components/card/card';
import { PixelTitleComponent } from '../../../shared/components/pixel-title/pixel-title';
import { PlayingCard } from '../../../shared/components/playing-card/playing-card';
import { TranslatePipe } from '../../../i18n';
import { HandReplay } from './hand-replay/hand-replay';

@Component({
  selector: 'app-poker-history',
  standalone: true,
  imports: [BadgeComponent, ButtonComponent, CardComponent, HandReplay, PixelTitleComponent,
            PlayingCard, RouterLink, TranslatePipe],
  templateUrl: './history.html',
  styleUrl: './history.scss',
})
export class PokerHistory implements OnInit {
  readonly history = inject(PokerHistoryService);
  readonly card = cardParts;
  /** Mano abierta en el replay, si hay alguna. */
  readonly replay = signal<PokerHandReplay | null>(null);

  ngOnInit(): void {
    this.history.loadHistory();
    this.history.loadStats();
    this.history.loadAchievements();
  }

  /** Icono de cada logro (es presentación, así que vive en el front). */
  iconFor(id: string): string {
    const iconos: Record<string, string> = {
      primera_mano: '🃏',
      escalera_de_color: '🌈',
      tres_seguidas: '🔥',
    };
    return iconos[id] ?? '🏅';
  }

  openMatch(match: PokerMatchSummary): void {
    this.history.loadMatch(match.game_id).subscribe({ error: () => undefined });
  }

  closeMatch(): void {
    this.history.closeMatch();
    this.replay.set(null);
  }

  /**
   * Abre el replay paso a paso de una mano (roadmap 7.2).
   *
   * El registro de acciones se pide al abrirla, no al listar: así la lista de manos no
   * carga con datos que casi nadie mira.
   */
  verMano(h: PokerHandView): void {
    this.history.loadReplay(h.id).subscribe({
      next: (mano) => this.replay.set(mano),
      error: () => this.history.error.set('poker.history.replayError'),
    });
  }

  cerrarReplay(): void {
    this.replay.set(null);
  }

  cards(field: string): string[] {
    return PokerHistoryService.cards(field);
  }

  resultVariant(match: PokerMatchSummary): 'success' | 'error' | 'default' {
    if (match.result === 'win') return 'success';
    if (match.result === 'loss') return 'error';
    return 'default';
  }

  trackMatch(_: number, m: PokerMatchSummary): number {
    return m.game_id;
  }

  trackHand(_: number, h: PokerHandView): number {
    return h.id;
  }

  formatDate(iso: string): string {
    const d = new Date(iso);
    return Number.isNaN(d.getTime())
      ? ''
      : d.toLocaleString(undefined, {
          day: '2-digit',
          month: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
        });
  }
}
