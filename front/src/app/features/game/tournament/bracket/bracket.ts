import { Component, Input } from '@angular/core';
import { AvatarComponent } from '../../../../shared/components/avatar/avatar';
import { BadgeComponent } from '../../../../shared/components/badge/badge';

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
  status: 'pending' | 'live' | 'completed';
}

export interface TournamentRound {
  id: string;
  name: string;
  matches: Match[];
}

@Component({
  selector: 'app-bracket',
  standalone: true,
  imports: [AvatarComponent, BadgeComponent],
  templateUrl: './bracket.html',
  styleUrl: './bracket.scss',
})
export class BracketComponent {
  @Input() rounds: TournamentRound[] = [];

  trackByRound(_: number, round: TournamentRound): string {
    return round.id;
  }

  trackByMatch(_: number, match: Match): string {
    return match.id;
  }
}
