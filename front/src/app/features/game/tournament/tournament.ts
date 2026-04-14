import { Component, signal, computed } from '@angular/core';
import { CardComponent } from '../../../shared/components/card/card';
import { BadgeComponent } from '../../../shared/components/badge/badge';
import { ButtonComponent } from '../../../shared/components/button/button';
import { BracketComponent, Match, Participant, TournamentRound } from './bracket/bracket';

export interface TournamentData {
  id: string;
  name: string;
  status: 'active' | 'upcoming' | 'finished';
  maxPlayers: number;
  currentPlayers: number;
  startDate: string;
  prize?: string;
  rounds: TournamentRound[];
}

@Component({
  selector: 'app-tournament',
  standalone: true,
  imports: [CardComponent, BadgeComponent, ButtonComponent, BracketComponent],
  templateUrl: './tournament.html',
  styleUrl: './tournament.scss',
})
export class Tournament {
  readonly selectedTab = signal<'active' | 'upcoming' | 'finished'>('active');
  readonly showRegisterModal = signal(false);
  readonly isRegistering = signal(false);

  readonly tournaments = signal<TournamentData[]>([
    {
      id: '1',
      name: 'Neon Championship',
      status: 'active',
      maxPlayers: 8,
      currentPlayers: 6,
      startDate: '2026-04-14',
      prize: '5000 coins',
      rounds: this.generateMockRounds(8),
    },
    {
      id: '2',
      name: 'Cyber Cup',
      status: 'active',
      maxPlayers: 16,
      currentPlayers: 16,
      startDate: '2026-04-13',
      prize: '10000 coins',
      rounds: this.generateMockRounds(16),
    },
    {
      id: '3',
      name: 'Pixel Masters',
      status: 'upcoming',
      maxPlayers: 8,
      currentPlayers: 3,
      startDate: '2026-04-20',
      prize: '3000 coins',
      rounds: [],
    },
    {
      id: '4',
      name: 'Retro Battle',
      status: 'upcoming',
      maxPlayers: 8,
      currentPlayers: 1,
      startDate: '2026-04-25',
      rounds: [],
    },
    {
      id: '5',
      name: 'First Blood',
      status: 'finished',
      maxPlayers: 8,
      currentPlayers: 8,
      startDate: '2026-04-10',
      prize: '2500 coins',
      rounds: this.generateMockRounds(8, true),
    },
  ]);

  readonly selectedTournament = signal<TournamentData | null>(null);

  readonly filteredTournaments = computed(() =>
    this.tournaments().filter((t) => t.status === this.selectedTab())
  );

  readonly activeCount = computed(() =>
    this.tournaments().filter((t) => t.status === 'active').length
  );

  readonly upcomingCount = computed(() =>
    this.tournaments().filter((t) => t.status === 'upcoming').length
  );

  readonly finishedCount = computed(() =>
    this.tournaments().filter((t) => t.status === 'finished').length
  );

  selectTab(tab: 'active' | 'upcoming' | 'finished') {
    this.selectedTab.set(tab);
  }

  selectTournament(tournament: TournamentData) {
    this.selectedTournament.set(tournament);
  }

  openRegisterModal() {
    this.showRegisterModal.set(true);
  }

  closeRegisterModal() {
    this.showRegisterModal.set(false);
  }

  registerForTournament() {
    this.isRegistering.set(true);
    setTimeout(() => {
      this.isRegistering.set(false);
      this.showRegisterModal.set(false);
    }, 1500);
  }

  getStatusBadge(status: TournamentData['status']): { variant: 'success' | 'warning' | 'default'; label: string } {
    switch (status) {
      case 'active':
        return { variant: 'success', label: 'Active' };
      case 'upcoming':
        return { variant: 'warning', label: 'Upcoming' };
      case 'finished':
        return { variant: 'default', label: 'Finished' };
    }
  }

  getProgressPercent(tournament: TournamentData): number {
    return Math.round((tournament.currentPlayers / tournament.maxPlayers) * 100);
  }

  private generateMockRounds(playerCount: number, finished = false): TournamentRound[] {
    const rounds: TournamentRound[] = [];
    const roundNames = this.getRoundNames(playerCount);
    let roundPlayerCount = playerCount;
    let roundIndex = 0;

    while (roundPlayerCount > 1) {
      const matches: Match[] = [];
      for (let i = 0; i < roundPlayerCount / 2; i++) {
        const hasWinner = finished || (roundIndex < rounds.length || Math.random() > 0.5);
        matches.push({
          id: `r${roundIndex}-m${i}`,
          player1: this.generateParticipant(roundPlayerCount, i * 2, finished),
          player2: this.generateParticipant(roundPlayerCount, i * 2 + 1, finished),
          winner: hasWinner && finished ? (Math.random() > 0.5 ? 1 : 2) : undefined,
          score: hasWinner ? `${Math.floor(Math.random() * 3)}-${Math.floor(Math.random() * 3)}` : undefined,
          status: finished ? 'completed' : roundIndex === 0 ? 'live' : 'pending',
        });
      }
      rounds.push({
        id: `round-${roundIndex}`,
        name: roundNames[roundIndex] || `Round ${roundIndex + 1}`,
        matches,
      });
      roundPlayerCount /= 2;
      roundIndex++;
    }

    return rounds;
  }

  private generateParticipant(roundCount: number, seed: number, isPast: boolean): Participant {
    const names = ['NeonKnight', 'PixelPrince', 'RetroRider', 'CyberMaster', 'ArcadeKing', 'GameWizard', 'ByteBoss', 'DataDragon'];
    return {
      id: `p-${seed}`,
      username: names[seed % names.length],
      avatarUrl: undefined,
      wins: Math.floor(Math.random() * 5),
      losses: Math.floor(Math.random() * 3),
      isEliminated: isPast && Math.random() > 0.6,
    };
  }

  private getRoundNames(count: number): string[] {
    if (count === 8) return ['Quarter-Finals', 'Semi-Finals', 'Final'];
    if (count === 16) return ['Round of 16', 'Quarter-Finals', 'Semi-Finals', 'Final'];
    return [];
  }
}
