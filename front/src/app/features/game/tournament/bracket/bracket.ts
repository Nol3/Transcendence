import { Component, EventEmitter, Input, Output } from '@angular/core';
import { AvatarComponent } from '../../../../shared/components/avatar/avatar';
import { BadgeComponent } from '../../../../shared/components/badge/badge';
import { TranslatePipe } from '../../../../i18n/translate.pipe';

export interface Participant {
  id: string;
  username: string;
  avatarUrl?: string;
  wins: number;
  losses: number;
  isEliminated?: boolean;
}

export interface Match {
  id: string;
  player1: Participant;
  player2: Participant;
  winner?: 1 | 2;
  score?: string;
  status: 'pending' | 'live' | 'awaiting_confirmation' | 'completed';
  /** Ganador declarado por un jugador, pendiente de que el rival lo confirme. */
  reportedWinnerSlot?: 1 | 2;
  /** Quién declaró ese resultado. */
  reportedBy?: { id: string; username: string };
}

export interface TournamentRound {
  id: string;
  name: string;
  matches: Match[];
}

export interface ReportMatchEvent {
  match: Match;
  winnerSlot: 1 | 2;
  player1Score: number;
  player2Score: number;
}

@Component({
  selector: 'app-bracket',
  standalone: true,
  imports: [AvatarComponent, BadgeComponent, TranslatePipe],
  templateUrl: './bracket.html',
  styleUrl: './bracket.scss',
})
export class BracketComponent {
  @Input() rounds: TournamentRound[] = [];
  /** Logged-in user id; enables actions on matches they play in. */
  @Input() currentUserId: string | null = null;
  /** Tournament creator can report any match (acts as referee). */
  @Input() canManage = false;

  /** Launch the actual game for this match. */
  @Output() readonly playMatch = new EventEmitter<Match>();
  /** Report a result directly from the bracket. */
  @Output() readonly reportMatch = new EventEmitter<ReportMatchEvent>();

  trackByRound(_: number, round: TournamentRound): string {
    return round.id;
  }

  trackByMatch(_: number, match: Match): string {
    return match.id;
  }

  /** A match is actionable when it's not finished, has two real players, and the
   *  current user takes part (or is the tournament creator/referee). */
  canAct(match: Match): boolean {
    if (match.status === 'completed') return false;
    if (!this.hasTwoPlayers(match)) return false;
    if (this.canManage) return true;
    return (
      this.currentUserId != null &&
      (match.player1.id === this.currentUserId || match.player2.id === this.currentUserId)
    );
  }

  hasTwoPlayers(match: Match): boolean {
    return match.player1?.id !== '?' && match.player2?.id !== '?';
  }

  /** Hay un resultado declarado esperando confirmación del rival. */
  isPending(match: Match): boolean {
    return match.status === 'awaiting_confirmation';
  }

  /** El usuario actual es quien debe confirmar (juega el match y no lo declaró él). */
  mustConfirm(match: Match): boolean {
    if (!this.isPending(match) || this.currentUserId == null) return false;
    const juega =
      match.player1.id === this.currentUserId || match.player2.id === this.currentUserId;
    return juega && match.reportedBy?.id !== this.currentUserId;
  }

  /** Texto de la etiqueta del botón de reporte, según toque declarar o confirmar. */
  reportLabel(match: Match, slot: 1 | 2): string {
    if (this.mustConfirm(match)) {
      return this.isReportedSlot(match, slot) ? '✔ Confirmar' : '✖ No estoy de acuerdo';
    }
    return slot === 1 ? match.player1.username : match.player2.username;
  }

  isReportedSlot(match: Match, slot: 1 | 2): boolean {
    return match.reportedWinnerSlot === slot;
  }

  report(match: Match, winnerSlot: 1 | 2): void {
    // Symbolic 1-0 score: explicit winner selection is what advances the bracket.
    this.reportMatch.emit({
      match,
      winnerSlot,
      player1Score: winnerSlot === 1 ? 1 : 0,
      player2Score: winnerSlot === 2 ? 1 : 0,
    });
  }
}
