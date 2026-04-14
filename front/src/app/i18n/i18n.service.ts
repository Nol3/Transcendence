import { Injectable, signal, computed, PLATFORM_ID, inject } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

export type Lang = 'en' | 'es' | 'fr';

const STORAGE_KEY = 'transcendence_lang';

interface TranslationDict {
  [key: string]: string | TranslationDict;
}

@Injectable({ providedIn: 'root' })
export class I18nService {
  private readonly platformId = inject(PLATFORM_ID);
  private readonly _currentLang = signal<Lang>('en');
  private _translations: Record<Lang, TranslationDict> = {
    en: {},
    es: {},
    fr: {},
  };
  private _loaded = signal(false);

  readonly currentLang = this._currentLang.asReadonly();
  readonly isLoaded = this._loaded.asReadonly();

  readonly langLabel = computed(() => {
    const labels: Record<Lang, string> = {
      en: 'English',
      es: 'Español',
      fr: 'Français',
    };
    return labels[this._currentLang()];
  });

  constructor() {
    if (isPlatformBrowser(this.platformId)) {
      this._currentLang.set(this.getStoredLang());
    }
  }

  async init(): Promise<void> {
    await Promise.all([this.loadLang('en'), this.loadLang('es'), this.loadLang('fr')]);
    this._loaded.set(true);
  }

  private async loadLang(lang: Lang): Promise<void> {
    try {
      const response = await fetch(`/i18n/${lang}.json`);
      if (response.ok) {
        this._translations[lang] = await response.json();
      }
    } catch {
      console.warn(`Failed to load translations for ${lang}`);
    }
  }

  setLang(lang: Lang): void {
    this._currentLang.set(lang);
    if (isPlatformBrowser(this.platformId)) {
      localStorage.setItem(STORAGE_KEY, lang);
    }
  }

  t(key: string, params?: Record<string, string | number>): string {
    const keys = key.split('.');
    let value: string | TranslationDict | undefined = this._translations[this._currentLang()];

    for (const k of keys) {
      if (value && typeof value === 'object' && k in value) {
        value = value[k];
      } else {
        return key;
      }
    }

    if (typeof value !== 'string') return key;

    if (params) {
      let result = value;
      Object.entries(params).forEach(([k, v]) => {
        result = result.replace(new RegExp(`{{${k}}}`, 'g'), String(v));
      });
      return result;
    }

    return value;
  }

  private getStoredLang(): Lang {
    if (isPlatformBrowser(this.platformId)) {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored && ['en', 'es', 'fr'].includes(stored)) {
        return stored as Lang;
      }
      const browserLang = navigator.language.split('-')[0];
      if (['en', 'es', 'fr'].includes(browserLang)) {
        return browserLang as Lang;
      }
    }
    return 'en';
  }
}
