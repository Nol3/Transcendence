import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, map, tap } from 'rxjs';

import { environment } from '../../../environments/environment';

export interface PokerOpponent {
  id: number;
  username: string;
}

export interface PokerMatchSummary {
  game_id: number;
  opponent: PokerOpponent | null;
  result: 'win' | 'loss' | 'draw';
  my_stack: number;
  opponent_stack: number;
  hands: number;
  rated: boolean;
  played_at: string;
}

export interface PokerHandPlayerView {
  seat: number;
  name: string;
  is_bot: boolean;
  hole: string;
  hand_name: string;
  stack_after: number;
  won: number;
  folded: boolean;
}

export interface PokerHandView {
  id: number;
  hand_number: number;
  board: string;
  pot: number;
  showdown: boolean;
  winner_names: string;
  created_at: string;
  players: PokerHandPlayerView[];
}

/** Un paso del registro de acciones de una mano, tal cual lo emite el motor. */
export interface PokerActionEvent {
  event: 'hand_start' | 'blind' | 'action' | 'street' | 'hand_end' | 'uncalled_return';
  seat?: number;
  kind?: string;
  action?: string;
  amount?: number;
  committed?: number;
  street?: string;
  board?: string[];
  stacks?: number[];
  button?: number;
  sb?: number;
  bb?: number;
  winner?: number;
  showdown?: boolean;
  pots?: unknown[];
  payouts?: Record<string, number>;
}

/** Una mano con su registro de acciones, para reproducirla paso a paso (roadmap 7.2). */
export interface PokerHandReplay extends PokerHandView {
  actions: PokerActionEvent[];
}

export interface PokerStats {
  hands_played: number;
  hands_won: number;
  showdowns: number;
  showdowns_won: number;
  biggest_pot: number;
  folded: number;
  win_rate: number;
}

/** Logro del póker (roadmap 7.1). */
export interface PokerAchievement {
  id: 'primera_mano' | 'escalera_de_color' | 'tres_seguidas';
  unlocked: boolean;
  progress: number;
  target: number;
}

/** Historial de póker: partidas jugadas, manos de cada partida y estadísticas. */
@Injectable({ providedIn: 'root' })
export class PokerHistoryService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/poker`;

  readonly matches = signal<PokerMatchSummary[]>([]);
  readonly hands = signal<PokerHandView[]>([]);
  readonly stats = signal<PokerStats | null>(null);
  readonly achievements = signal<PokerAchievement[]>([]);
  readonly activeGameId = signal<number | null>(null);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);

  loadHistory(): void {
    this.loading.set(true);
    this.http
      .get<{ count: number; results: PokerMatchSummary[] }>(`${this.base}/history/`)
      .subscribe({
        next: (res) => {
          this.matches.set(res.results ?? []);
          this.loading.set(false);
        },
        error: () => {
          this.error.set('poker.history.error');
          this.loading.set(false);
        },
      });
  }

  loadStats(): void {
    this.http.get<PokerStats>(`${this.base}/stats/`).subscribe({
      next: (stats) => this.stats.set(stats),
      error: () => this.stats.set(null),
    });
  }

  loadAchievements(): void {
    this.http
      .get<{ achievements: PokerAchievement[] }>(`${this.base}/achievements/`)
      .subscribe({
        next: (res) => this.achievements.set(res.achievements ?? []),
        error: () => this.achievements.set([]),
      });
  }

  /** Manos de una partida concreta. */
  loadMatch(gameId: number): Observable<PokerHandView[]> {
    return this.http
      .get<{ game_id: number; results: PokerHandView[] }>(`${this.base}/history/${gameId}/`)
      .pipe(
        map((res) => res.results ?? []),
        tap((manos) => {
          this.activeGameId.set(gameId);
          this.hands.set(manos);
        }),
      );
  }

  /**
   * Una mano concreta con su registro de acciones, para el replay paso a paso.
   *
   * Va aparte de `loadMatch` a propósito: el registro pesa y solo hace falta cuando
   * alguien abre una mano.
   */
  loadReplay(handId: number): Observable<PokerHandReplay> {
    return this.http.get<PokerHandReplay>(`${this.base}/history/hand/${handId}/`);
  }

  closeMatch(): void {
    this.activeGameId.set(null);
    this.hands.set([]);
  }

  clearError(): void {
    this.error.set(null);
  }

  /** Cartas "7c 2s" → lista de cartas para pintarlas. */
  static cards(field: string): string[] {
    return (field || '').split(/\s+/).filter(Boolean);
  }
}
