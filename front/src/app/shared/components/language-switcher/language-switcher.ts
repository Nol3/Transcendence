export type Lang = 'en' | 'es' | 'fr';

export interface LanguageOption {
  code: Lang;
  label: string;
  flag: string;
}

export const LANGUAGES: LanguageOption[] = [
  { code: 'en', label: 'English', flag: '🇬🇧' },
  { code: 'es', label: 'Español', flag: '🇪🇸' },
  { code: 'fr', label: 'Français', flag: '🇫🇷' },
];

import { Component, inject, signal, HostListener, ElementRef } from '@angular/core';
import { UpperCasePipe } from '@angular/common';
import { I18nService } from '../../../i18n/i18n.service';

@Component({
  selector: 'app-language-switcher',
  standalone: true,
  imports: [UpperCasePipe],
  templateUrl: './language-switcher.html',
  styleUrl: './language-switcher.scss',
})
export class LanguageSwitcherComponent {
  private readonly i18n = inject(I18nService);
  private readonly el = inject(ElementRef);

  readonly languages: LanguageOption[] = LANGUAGES;
  readonly isOpen = signal(false);

  get currentLangData(): LanguageOption {
    const current = this.i18n.currentLang();
    return this.languages.find((l: LanguageOption) => l.code === current) ?? this.languages[0];
  }

  get currentCode(): Lang {
    return this.i18n.currentLang();
  }

  toggle() {
    this.isOpen.update(v => !v);
  }

  select(code: Lang) {
    this.i18n.setLang(code);
    this.isOpen.set(false);
  }

  @HostListener('document:click', ['$event'])
  onClickOutside(event: Event) {
    if (!this.el.nativeElement.contains(event.target)) {
      this.isOpen.set(false);
    }
  }
}
