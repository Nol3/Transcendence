import { Component, signal } from '@angular/core';
import { UpperCasePipe } from '@angular/common';

export type Lang = 'en' | 'es' | 'fr';

export const LANGUAGES: { code: Lang; label: string; flag: string }[] = [
  { code: 'en', label: 'English', flag: '🇬🇧' },
  { code: 'es', label: 'Español', flag: '🇪🇸' },
  { code: 'fr', label: 'Français', flag: '🇫🇷' },
];

@Component({
  selector: 'app-language-switcher',
  standalone: true,
  imports: [UpperCasePipe],
  templateUrl: './language-switcher.html',
  styleUrl: './language-switcher.scss',
})
export class LanguageSwitcherComponent {
  readonly languages = LANGUAGES;
  readonly current = signal<Lang>('en');
  readonly open = signal(false);

  get currentLang() {
    return this.languages.find((l) => l.code === this.current()) ?? this.languages[0];
  }

  select(code: Lang) {
    this.current.set(code);
    this.open.set(false);
    // i18n service integration point — Step 6
  }

  toggle() { this.open.update((v) => !v); }
}
