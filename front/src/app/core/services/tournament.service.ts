import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, map } from 'rxjs';
import { environment } from '../../../environments/environment';

export type TournamentStatus = 'pending' | 'in_progress' | 'finished';
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
  max_players: number;
  prize?: string;
}

interface BackendUser {
  id: number;
  username: string;
  avatar?: string;
}

interface BackendParticipant {
  id: number;
  user: BackendUser;
  joined_at: string;
}

interface BackendTournament {
  id: number;
  name: string;
  description?: string;
  creator: BackendUser;
  max_players: number;
  status: TournamentStatus;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  participants: BackendParticipant[];
}

const ACCESS_TOKEN_KEY = 'access_token';

@Injectable({ providedIn: 'root' })
export class TournamentService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/tournament`;
  private readonly _currentTournament = signal<Tournament | null>(null);
  private ws: WebSocket | null = null;

  readonly currentTournament = this._currentTournament.asReadonly();

  private currentUserId(): number | null {
    if (typeof localStorage === 'undefined') return null;
    const raw = localStorage.getItem('user');
    if (!raw) return null;
    try {
      const u = JSON.parse(raw);
      return typeof u?.id === 'number' ? u.id : null;
    } catch {
      return null;
    }
  }

  private adapt(t: BackendTournament): Tournament {
    const startDate = t.started_at ?? t.created_at;
    const myId = this.currentUserId();
    return {
      id: String(t.id),
      name: t.name,
      description: t.description,
      status: t.status,
      maxPlayers: t.max_players,
      currentPlayers: t.participants?.length ?? 0,
      prize: undefined,
      startDate: startDate.slice(0, 10),
      rounds: [],
      isRegistered: myId != null && (t.participants ?? []).some((p) => p.user?.id === myId),
    };
  }

  getTournaments(status?: TournamentStatus): Observable<Tournament[]> {
    return this.http.get<BackendTournament[]>(`${this.baseUrl}/`).pipe(
      map((list) => {
        const adapted = list.map((t) => this.adapt(t));
        return status ? adapted.filter((t) => t.status === status) : adapted;
      }),
    );
  }

  getTournament(id: string): Observable<Tournament> {
    return this.http.get<BackendTournament>(`${this.baseUrl}/${id}/`).pipe(
      map((t) => {
        const adapted = this.adapt(t);
        this._currentTournament.set(adapted);
        return adapted;
      }),
    );
  }

  createTournament(payload: CreateTournamentPayload): Observable<Tournament> {
    return this.http
      .post<BackendTournament>(`${this.baseUrl}/create_tournament/`, payload)
      .pipe(map((t) => this.adapt(t)));
  }

  joinTournament(id: string): Observable<void> {
    return this.http.post<unknown>(`${this.baseUrl}/${id}/join/`, {}).pipe(map(() => undefined));
  }

  leaveTournament(id: string): Observable<void> {
    return this.http.post<unknown>(`${this.baseUrl}/${id}/leave/`, {}).pipe(map(() => undefined));
  }

  connectToTournamentUpdates(
    tournamentId: string,
    onUpdate: (tournament: Tournament) => void,
  ): void {
    const token =
      typeof localStorage !== 'undefined' ? localStorage.getItem(ACCESS_TOKEN_KEY) : null;
    if (!token) return;

    this.ws = new WebSocket(`${environment.wsUrl}/tournaments/${tournamentId}?token=${token}`);

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'tournament_update' || data.type === 'match_update') {
          onUpdate(data.tournament);
        }
      } catch {
        // ignore malformed payloads
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
