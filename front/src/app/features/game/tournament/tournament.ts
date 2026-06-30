import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { CardComponent } from '../../../shared/components/card/card';
import { BadgeComponent } from '../../../shared/components/badge/badge';
import { ButtonComponent } from '../../../shared/components/button/button';
import { SpinnerComponent } from '../../../shared/components/spinner/spinner';
import { BracketComponent, Match, ReportMatchEvent, TournamentRound } from './bracket/bracket';
import {
  Tournament as ApiTournament,
  TournamentService,
  TournamentStatus as ApiTournamentStatus,
} from '../../../core/services/tournament.service';
import { NotificationService } from '../../../core/services/notification.service';
import { TranslatePipe } from '../../../i18n/translate.pipe';

export type UiTournamentStatus = 'active' | 'upcoming' | 'finished';

export interface TournamentData {
  id: string;
  name: string;
  status: UiTournamentStatus;
  maxPlayers: number;
  currentPlayers: number;
  startDate: string;
  prize?: string;
  rounds: TournamentRound[];
  isRegistered: boolean;
  creatorId: string | null;
}

const STATUS_API_TO_UI: Record<ApiTournamentStatus, UiTournamentStatus> = {
  pending: 'upcoming',
  in_progress: 'active',
  finished: 'finished',
};

@Component({
  selector: 'app-tournament',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    CardComponent,
    BadgeComponent,
    ButtonComponent,
    SpinnerComponent,
    BracketComponent,
    TranslatePipe,
  ],
  templateUrl: './tournament.html',
  styleUrl: './tournament.scss',
})
export class Tournament implements OnInit, OnDestroy {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(TournamentService);
  private readonly notif = inject(NotificationService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  /** Logged-in user id, to decide which matches expose actions. */
  readonly currentUserId = this.api.myUserId();

  readonly selectedTab = signal<UiTournamentStatus>('active');
  readonly showCreateModal = signal(false);
  readonly isCreating = signal(false);
  readonly isJoining = signal(false);
  readonly isLoading = signal(true);
  readonly isReporting = signal(false);

  readonly tournaments = signal<TournamentData[]>([]);
  readonly selectedTournament = signal<TournamentData | null>(null);

  /** The creator can report any match (acts as referee), handy for local play. */
  readonly canManageSelected = computed(() => {
    const t = this.selectedTournament();
    return !!t && this.currentUserId != null && t.creatorId === this.currentUserId;
  });

  // Backend validates max_players in [4, 32]; keep the form in lockstep (M2).
  readonly createForm: FormGroup = this.fb.group({
    name: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(100)]],
    maxPlayers: [8, [Validators.required, Validators.min(4), Validators.max(32)]],
    description: [''],
  });

  readonly filteredTournaments = computed(() =>
    this.tournaments().filter((t) => t.status === this.selectedTab()),
  );

  readonly activeCount = computed(
    () => this.tournaments().filter((t) => t.status === 'active').length,
  );
  readonly upcomingCount = computed(
    () => this.tournaments().filter((t) => t.status === 'upcoming').length,
  );
  readonly finishedCount = computed(
    () => this.tournaments().filter((t) => t.status === 'finished').length,
  );

  ngOnInit(): void {
    this.loadTournaments();
    // Deep link support: /tournament/:id opens that tournament's detail directly.
    const id = this.route.snapshot.paramMap.get('id');
    if (id) this.openTournamentById(id);
  }

  ngOnDestroy(): void {
    this.api.disconnect();
  }

  private toUi(t: ApiTournament): TournamentData {
    return {
      id: t.id,
      name: t.name,
      status: STATUS_API_TO_UI[t.status],
      maxPlayers: t.maxPlayers,
      currentPlayers: t.currentPlayers,
      startDate: t.startDate,
      prize: t.prize,
      rounds: t.rounds.map((r) => ({
        id: r.id,
        name: r.name,
        matches: r.matches.map((m) => ({
          id: m.id,
          player1: {
            id: m.player1?.id ?? '?',
            username: m.player1?.username ?? 'TBD',
            wins: 0,
            losses: 0,
            isEliminated: m.player1?.isEliminated ?? false,
          },
          player2: {
            id: m.player2?.id ?? '?',
            username: m.player2?.username ?? 'TBD',
            wins: 0,
            losses: 0,
            isEliminated: m.player2?.isEliminated ?? false,
          },
          winner: m.winner,
          score: m.score,
          status: m.status,
        })),
      })),
      isRegistered: t.isRegistered,
      creatorId: t.creatorId,
    };
  }

  loadTournaments(): void {
    this.isLoading.set(true);
    this.api.getTournaments().subscribe({
      next: (list) => {
        this.tournaments.set(list.map((t) => this.toUi(t)));
        this.isLoading.set(false);
      },
      error: () => {
        this.tournaments.set([]);
        this.isLoading.set(false);
      },
    });
  }

  selectTab(tab: UiTournamentStatus) {
    this.selectedTab.set(tab);
  }

  selectTournament(tournament: TournamentData) {
    // Show what we have immediately, then fetch the full bracket and subscribe
    // to live updates over the WebSocket.
    this.selectedTournament.set(tournament);
    this.openTournamentById(tournament.id);
  }

  /** Load a tournament's full detail and open a live WebSocket subscription. */
  private openTournamentById(id: string): void {
    this.api.getTournament(id).subscribe({
      next: (full) => this.selectedTournament.set(this.toUi(full)),
      error: () => {
        /* keep whatever snapshot we already had */
      },
    });
    // Live bracket: the backend pushes the fresh state on every change.
    this.api.connectToTournamentUpdates(id, (updated) => {
      this.selectedTournament.set(this.toUi(updated));
      // Keep the list view in sync too.
      this.tournaments.update((list) =>
        list.map((t) => (t.id === updated.id ? this.toUi(updated) : t)),
      );
    });
  }

  closeDetail(): void {
    this.api.disconnect();
    this.selectedTournament.set(null);
  }

  /** Launch the actual game for a bracket match (game reports back the result). */
  handlePlayMatch(match: Match): void {
    const t = this.selectedTournament();
    if (!t) return;
    this.router.navigate(['/game'], {
      queryParams: {
        tournament: t.id,
        match: match.id,
        p1: match.player1.username,
        p2: match.player2.username,
      },
    });
  }

  /** Report a result straight from the bracket; backend advances + broadcasts. */
  handleReportMatch(event: ReportMatchEvent): void {
    const t = this.selectedTournament();
    if (!t) return;
    this.isReporting.set(true);
    this.api
      .reportMatchResult(t.id, event.match.id, {
        winner_slot: event.winnerSlot,
        player1_score: event.player1Score,
        player2_score: event.player2Score,
      })
      .subscribe({
        next: (updated) => {
          this.selectedTournament.set(this.toUi(updated));
          this.tournaments.update((list) =>
            list.map((x) => (x.id === updated.id ? this.toUi(updated) : x)),
          );
          this.isReporting.set(false);
          this.notif.success('Result reported', t.name);
        },
        error: () => {
          this.isReporting.set(false);
          this.notif.error('Report failed', 'Could not report the match result');
        },
      });
  }

  openCreateModal() {
    this.createForm.reset({ name: '', maxPlayers: 8, description: '' });
    this.showCreateModal.set(true);
  }

  closeCreateModal() {
    this.showCreateModal.set(false);
  }

  createTournament() {
    if (this.createForm.invalid) {
      this.createForm.markAllAsTouched();
      return;
    }

    const { name, maxPlayers, description } = this.createForm.value;
    this.isCreating.set(true);
    this.api
      .createTournament({
        name,
        max_players: Number(maxPlayers),
        description: description || undefined,
      })
      .subscribe({
        next: (created) => {
          this.tournaments.update((list) => [this.toUi(created), ...list]);
          this.notif.success('Tournament Created', created.name);
          this.isCreating.set(false);
          this.showCreateModal.set(false);
        },
        error: () => {
          this.isCreating.set(false);
          this.notif.error('Create Failed', 'Could not create tournament');
        },
      });
  }

  joinTournament(tournament: TournamentData) {
    if (tournament.isRegistered) return;
    this.isJoining.set(true);
    this.api.joinTournament(tournament.id).subscribe({
      next: () => {
        this.tournaments.update((list) =>
          list.map((t) =>
            t.id === tournament.id
              ? { ...t, isRegistered: true, currentPlayers: t.currentPlayers + 1 }
              : t,
          ),
        );
        this.notif.success('Joined', tournament.name);
        this.isJoining.set(false);
      },
      error: () => {
        this.isJoining.set(false);
        this.notif.error('Join Failed', 'Could not join tournament');
      },
    });
  }

  getStatusBadge(status: UiTournamentStatus): {
    variant: 'success' | 'warning' | 'default';
    label: string;
  } {
    switch (status) {
      case 'active':
        return { variant: 'success', label: 'Active' };
      case 'upcoming':
        return { variant: 'warning', label: 'Upcoming' };
      case 'finished':
        return { variant: 'default', label: 'Finished' };
    }
  }

  getProgressPercent(t: TournamentData): number {
    return t.maxPlayers === 0 ? 0 : Math.round((t.currentPlayers / t.maxPlayers) * 100);
  }
}
