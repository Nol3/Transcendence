import { Injectable, inject, signal } from '@angular/core';
import { Observable, tap, map } from 'rxjs';
import { ApiService } from './api.service';
import { environment } from '../../../environments/environment';

export type TournamentStatus = 'registration' | 'active' | 'finished';
export type MatchStatus = 'pending' | 'live' | 'completed';

export interface TournamentParticipant {
  id: string;
  username: string;
  avatar?: string;
  isEliminated: boolean;
}

export interface TournamentMatch {
  id: string;
  round: number;
  position: number;
  player1?: TournamentParticipant;
  player2?: TournamentParticipant;
  winner?: 1 | 2;
  score?: string;
  status: MatchStatus;
}

export interface TournamentRound {
  id: string;
  name: string;
  matches: TournamentMatch[];
}

export interface Tournament {
  id: string;
  name: string;
  description?: string;
  status: TournamentStatus;
  maxPlayers: number;
  currentPlayers: number;
  prize?: string;
  startDate: string;
  rounds: TournamentRound[];
  isRegistered: boolean;
}

export interface CreateTournamentPayload {
  name: string;
  description?: string;
  maxPlayers: number;
  startDate: string;
  prize?: string;
}

@Injectable({ providedIn: 'root' })
export class TournamentService {
  private readonly api = inject(ApiService);
  private readonly _currentTournament = signal<Tournament | null>(null);
  private ws: WebSocket | null = null;

  readonly currentTournament = this._currentTournament.asReadonly();

  getTournaments(status?: TournamentStatus): Observable<Tournament[]> {
    const params: Record<string, string> = {};
    if (status) {
      params['status'] = status;
    }
    return this.api.getPaginated<Tournament>('/tournaments', params).pipe(
      map((res) => res.data)
    );
  }

  getTournament(id: string): Observable<Tournament> {
    return this.api.get<{ tournament: Tournament }>(`/tournaments/${id}`).pipe(
      tap((res) => {
        if (res.data) {
          this._currentTournament.set(res.data.tournament);
        }
      }),
      map((res) => res.data!.tournament)
    );
  }

  createTournament(payload: CreateTournamentPayload): Observable<Tournament> {
    return this.api.post<{ tournament: Tournament }>('/tournaments', payload).pipe(
      map((res) => res.data!.tournament)
    );
  }

  registerForTournament(id: string): Observable<Tournament> {
    return this.api.post<{ tournament: Tournament }>(`/tournaments/${id}/register`, {}).pipe(
      map((res) => res.data!.tournament)
    );
  }

  unregisterFromTournament(id: string): Observable<void> {
    return this.api.post<null>(`/tournaments/${id}/unregister`, {}).pipe(
      map(() => undefined)
    );
  }

  connectToTournamentUpdates(tournamentId: string, onUpdate: (tournament: Tournament) => void): void {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    this.ws = new WebSocket(`${environment.wsUrl}/tournaments/${tournamentId}?token=${token}`);

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'tournament_update') {
        onUpdate(data.tournament);
      } else if (data.type === 'match_update') {
        onUpdate(data.tournament);
      }
    };

    this.ws.onerror = () => {
      console.error('Tournament WebSocket error');
    };

    this.ws.onclose = () => {
      this.ws = null;
    };
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this._currentTournament.set(null);
  }
}
