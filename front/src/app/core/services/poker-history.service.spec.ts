import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { PokerHistoryService } from './poker-history.service';

describe('PokerHistoryService', () => {
  let service: PokerHistoryService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(PokerHistoryService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('parte el campo de cartas en cartas sueltas', () => {
    expect(PokerHistoryService.cards('7c 2s Ad Td 9d')).toEqual(['7c', '2s', 'Ad', 'Td', '9d']);
    expect(PokerHistoryService.cards('')).toEqual([]);
  });

  it('carga el listado de partidas', () => {
    service.loadHistory();
    http.expectOne((r) => r.url.endsWith('/poker/history/')).flush({
      count: 1,
      results: [{
        game_id: 1, opponent: { id: 2, username: 'rival' }, result: 'win',
        my_stack: 1400, opponent_stack: 600, hands: 3, rated: true,
        played_at: '2026-07-01T10:00:00Z',
      }],
    });

    expect(service.matches().length).toBe(1);
    expect(service.matches()[0].opponent?.username).toBe('rival');
    expect(service.loading()).toBe(false);
  });

  it('carga las estadísticas', () => {
    service.loadStats();
    http.expectOne((r) => r.url.endsWith('/poker/stats/')).flush({
      hands_played: 12, hands_won: 5, showdowns: 6, showdowns_won: 2,
      biggest_pot: 240, folded: 4, win_rate: 41.7,
    });
    expect(service.stats()?.biggest_pot).toBe(240);
    expect(service.stats()?.win_rate).toBe(41.7);
  });

  it('carga las manos de una partida y marca cuál está abierta', () => {
    service.loadMatch(7).subscribe();
    http.expectOne((r) => r.url.endsWith('/poker/history/7/')).flush({
      game_id: 7,
      results: [{
        id: 11, hand_number: 1, board: '7c 2s Ad Td 9d', pot: 240, showdown: true,
        winner_names: 'ana', created_at: '2026-07-01T10:00:00Z',
        players: [
          { seat: 0, name: 'ana', is_bot: false, hole: '8c Ts', hand_name: 'Pareja',
            stack_after: 1400, won: 240, folded: false },
        ],
      }],
    });

    expect(service.activeGameId()).toBe(7);
    expect(service.hands()[0].pot).toBe(240);
    expect(service.hands()[0].players[0].hand_name).toBe('Pareja');

    service.closeMatch();
    expect(service.activeGameId()).toBeNull();
    expect(service.hands()).toEqual([]);
  });

  it('si el historial falla lo dice y no deja datos a medias', () => {
    service.loadHistory();
    http
      .expectOne((r) => r.url.endsWith('/poker/history/'))
      .flush('boom', { status: 500, statusText: 'Server error' });
    expect(service.error()).toBe('poker.history.error');
    expect(service.matches()).toEqual([]);
  });
});
