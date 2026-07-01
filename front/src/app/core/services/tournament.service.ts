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
  creatorId: string | null;
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
  is_eliminated?: boolean;
  joined_at: string;
}

interface BackendMatchPlayer {
  id: number;
  username: string;
  avatar?: string | null;
}

interface BackendMatch {
  id: number;
  round: number;
  position: number;
  player1: BackendMatchPlayer | null;
  player2: BackendMatchPlayer | null;
  winner_slot: 1 | 2 | null;
  player1_score: number;
  player2_score: number;
  status: MatchStatus;
}

interface BackendRound {
  id: number;
  number: number;
  name: string;
  matches: BackendMatch[];
}

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
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
  rounds?: BackendRound[];
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
    const raw = localStorage.getItem('current_user');
    if (!raw) return null;
    try {
      const u = JSON.parse(raw);
      return typeof u?.id === 'number' ? u.id : null;
    } catch {
      return null;
    }
  }

  /** Public, string form of the logged-in user id (UI compares against slot ids). */
  myUserId(): string | null {
    const id = this.currentUserId();
    return id == null ? null : String(id);
  }

  private adapt(t: BackendTournament): Tournament {
    const startDate = t.started_at ?? t.created_at;
    const myId = this.currentUserId();

    // Map userId → elimination flag so bracket slots can be greyed out.
    const eliminated = new Map<number, boolean>();
    for (const p of t.participants ?? []) {
      if (p.user?.id != null) eliminated.set(p.user.id, !!p.is_eliminated);
    }

    return {
      id: String(t.id),
      name: t.name,
      description: t.description,
      status: t.status,
      maxPlayers: t.max_players,
      currentPlayers: t.participants?.length ?? 0,
      prize: undefined,
      startDate: startDate.slice(0, 10),
      rounds: (t.rounds ?? []).map((r) => this.adaptRound(r, eliminated)),
      isRegistered: myId != null && (t.participants ?? []).some((p) => p.user?.id === myId),
      creatorId: t.creator?.id != null ? String(t.creator.id) : null,
    };
  }

  private adaptRound(r: BackendRound, eliminated: Map<number, boolean>): TournamentRound {
    return {
      id: String(r.id),
      name: r.name,
      matches: (r.matches ?? []).map((m) => this.adaptMatch(m, eliminated)),
    };
  }

  private adaptMatch(m: BackendMatch, eliminated: Map<number, boolean>): TournamentMatch {
    const toPlayer = (p: BackendMatchPlayer | null): TournamentParticipant | undefined =>
      p
        ? {
            id: String(p.id),
            username: p.username,
            avatar: p.avatar ?? undefined,
            isEliminated: eliminated.get(p.id) ?? false,
          }
        : undefined;

    return {
      id: String(m.id),
      round: m.round,
      position: m.position,
      player1: toPlayer(m.player1),
      player2: toPlayer(m.player2),
      winner: m.winner_slot ?? undefined,
      score: m.status === 'completed' ? `${m.player1_score}-${m.player2_score}` : undefined,
      status: m.status,
    };
  }

  getTournaments(status?: TournamentStatus): Observable<Tournament[]> {
    return this.http
      .get<PaginatedResponse<BackendTournament>>(`${this.baseUrl}/`)
      .pipe(
        map((response) => {
          const adapted = response.results.map((t) => this.adapt(t));
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

  /** Report a tournament match result; backend advances the bracket + broadcasts. */
  reportMatchResult(
    tournamentId: string,
    matchId: string,
    payload: { winner_slot: 1 | 2; player1_score: number; player2_score: number },
  ): Observable<Tournament> {
    return this.http
      .post<BackendTournament>(
        `${this.baseUrl}/${tournamentId}/matches/${matchId}/result/`,
        payload,
      )
      .pipe(
        map((t) => {
          const adapted = this.adapt(t);
          this._currentTournament.set(adapted);
          return adapted;
        }),
      );
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
        if (
          (data.type === 'tournament_update' || data.type === 'match_update') &&
          data.tournament
        ) {
          // The consumer pushes the raw backend payload; adapt it to the UI shape
          // (and cache it) before handing it to the caller.
          const adapted = this.adapt(data.tournament as BackendTournament);
          this._currentTournament.set(adapted);
          onUpdate(adapted);
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
