import { Component, Input, computed, signal } from '@angular/core';

export type AvatarSize = 'sm' | 'md' | 'lg' | 'xl';

@Component({
  selector: 'app-avatar',
  standalone: true,
  templateUrl: './avatar.html',
  styleUrl: './avatar.scss',
})
export class AvatarComponent {
  @Input() src?: string | null;
  @Input() username = '';
  @Input() size: AvatarSize = 'md';

  readonly imgError = signal(false);

  get initials(): string {
    return this.username.slice(0, 2).toUpperCase() || '??';
  }

  get showImage(): boolean {
    return !!this.src && !this.imgError();
  }

  onImgError() { this.imgError.set(true); }
}
