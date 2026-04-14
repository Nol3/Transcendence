import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { DatePipe } from '@angular/common';
import { AuthService } from '../../core/services/auth.service';
import { NotificationService } from '../../core/services/notification.service';
import { UserService, UserStats, GameHistoryEntry } from '../../core/services/user.service';
import { AvatarComponent } from '../../shared/components/avatar/avatar';
import { ButtonComponent } from '../../shared/components/button/button';
import { CardComponent } from '../../shared/components/card/card';
import { InputComponent } from '../../shared/components/input/input';
import { BadgeComponent } from '../../shared/components/badge/badge';
import { DividerComponent } from '../../shared/components/divider/divider';
import { SpinnerComponent } from '../../shared/components/spinner/spinner';
import { TranslatePipe } from '../../i18n/translate.pipe';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    DatePipe,
    AvatarComponent,
    ButtonComponent,
    CardComponent,
    InputComponent,
    BadgeComponent,
    DividerComponent,
    SpinnerComponent,
    TranslatePipe,
  ],
  templateUrl: './profile.html',
  styleUrl: './profile.scss',
})
export class Profile implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly notif = inject(NotificationService);
  private readonly userService = inject(UserService);

  readonly user = this.auth.user;
  readonly isEditing = signal(false);
  readonly isLoading = signal(false);
  readonly isSaving = signal(false);
  readonly avatarPreview = signal<string | null>(null);
  readonly statsLoading = signal(true);
  readonly historyLoading = signal(true);

  readonly stats = signal<UserStats | null>(null);
  readonly history = signal<GameHistoryEntry[]>([]);

  readonly profileForm: FormGroup = this.fb.group({
    username: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(20), Validators.pattern(/^[a-zA-Z0-9_]+$/)]],
  });

  readonly rankLabel = computed(() => {
    const rank = this.stats()?.rank ?? 999;
    if (rank === 1) return 'CHAMPION';
    if (rank === 2) return 'MASTER';
    if (rank <= 5) return 'EXPERT';
    if (rank <= 10) return 'SKILLED';
    return 'ROOKIE';
  });

  ngOnInit(): void {
    if (this.user()) {
      this.profileForm.patchValue({ username: this.user()!.username });
      this.loadUserData();
    }
  }

  private loadUserData(): void {
    this.userService.getUserStats().subscribe({
      next: (data) => {
        this.stats.set(data);
        this.statsLoading.set(false);
      },
      error: () => {
        this.stats.set({
          wins: 0,
          losses: 0,
          rank: 999,
          winRate: 0,
          gamesPlayed: 0,
          currentStreak: 0,
          longestStreak: 0,
        });
        this.statsLoading.set(false);
      },
    });

    this.userService.getUserHistory().subscribe({
      next: (data) => {
        this.history.set(data);
        this.historyLoading.set(false);
      },
      error: () => {
        this.history.set([]);
        this.historyLoading.set(false);
      },
    });
  }

  startEditing() {
    this.isEditing.set(true);
    this.profileForm.patchValue({ username: this.user()?.username ?? '' });
  }

  cancelEditing() {
    this.isEditing.set(false);
    this.profileForm.reset({ username: this.user()?.username ?? '' });
    this.avatarPreview.set(null);
  }

  onAvatarChange(event: Event) {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (file) {
      if (file.size > 5 * 1024 * 1024) {
        this.notif.error('File Too Large', 'Avatar must be under 5MB');
        return;
      }

      const reader = new FileReader();
      reader.onload = () => {
        this.avatarPreview.set(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  }

  saveProfile() {
    if (this.profileForm.invalid) {
      this.profileForm.markAllAsTouched();
      return;
    }

    const newUsername = this.profileForm.get('username')?.value as string;
    const avatarFile = (document.querySelector('input[type="file"]') as HTMLInputElement)?.files?.[0];

    this.isSaving.set(true);

    const usernameChanged = newUsername && newUsername !== this.user()?.username;

    if (avatarFile) {
      this.auth.uploadAvatar(avatarFile).subscribe({
        next: () => {
          if (usernameChanged) {
            this.auth.updateProfile({ username: newUsername }).subscribe({
              next: () => this.finishSave(),
              error: () => this.finishSave(),
            });
          } else {
            this.finishSave();
          }
        },
        error: () => {
          this.isSaving.set(false);
          this.notif.error('Upload Failed', 'Could not upload avatar');
        },
      });
    } else if (usernameChanged) {
      this.auth.updateProfile({ username: newUsername }).subscribe({
        next: () => this.finishSave(),
        error: () => this.finishSave(),
      });
    } else {
      this.finishSave();
    }
  }

  private finishSave() {
    this.isSaving.set(false);
    this.isEditing.set(false);
    this.avatarPreview.set(null);
  }

  getError(field: string): string {
    const control = this.profileForm.get(field);
    if (!control?.errors || !control.touched) return '';

    if (control.errors['required']) return 'This field is required';
    if (control.errors['minlength']) return `Minimum ${control.errors['minlength'].requiredLength} characters`;
    if (control.errors['maxlength']) return `Maximum ${control.errors['maxlength'].requiredLength} characters`;
    if (control.errors['pattern']) return 'Only letters, numbers and underscores allowed';

    return 'Invalid value';
  }

  trackByGame(_: number, game: GameHistoryEntry): string {
    return game.id;
  }
}
