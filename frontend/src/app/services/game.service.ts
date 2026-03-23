import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Game } from '../models';

@Injectable({
  providedIn: 'root'
})
export class GameService {
  private apiUrl = '/api/games';

  constructor(private http: HttpClient) {}

  getMyGames(): Observable<Game[]> {
    return this.http.get<Game[]>(`${this.apiUrl}/my_games/`);
  }

  getGame(id: number): Observable<Game> {
    return this.http.get<Game>(`${this.apiUrl}/${id}/`);
  }

  createGame(player2Id: number): Observable<Game> {
    return this.http.post<Game>(`${this.apiUrl}/create_game/`, {
      player2_id: player2Id
    });
  }

  updateGameScore(gameId: number, player1Score: number, player2Score: number): Observable<Game> {
    return this.http.patch<Game>(`${this.apiUrl}/${gameId}/`, {
      player1_score: player1Score,
      player2_score: player2Score
    });
  }
}
