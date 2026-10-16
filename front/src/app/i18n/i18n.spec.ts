import { TestBed } from '@angular/core/testing';

import { I18nService, Lang } from './i18n.service';
import en from '../../../public/i18n/en.json';
import es from '../../../public/i18n/es.json';
import fr from '../../../public/i18n/fr.json';

const DICS: Record<Lang, Record<string, unknown>> = { en, es, fr };
const IDIOMAS: Lang[] = ['en', 'es', 'fr'];

function aplanar(d: Record<string, unknown>, prefijo = ''): string[] {
  const claves: string[] = [];
  for (const [k, v] of Object.entries(d)) {
    if (v && typeof v === 'object') {
      claves.push(...aplanar(v as Record<string, unknown>, `${prefijo}${k}.`));
    } else {
      claves.push(`${prefijo}${k}`);
    }
  }
  return claves.sort();
}

function valor(d: Record<string, unknown>, clave: string): unknown {
  let v: unknown = d;
  for (const p of clave.split('.')) v = (v as Record<string, unknown>)?.[p];
  return v;
}

const parametros = (s: string) => (s.match(/\{\{\w+\}\}/g) ?? []).sort();

describe('i18n — paridad de claves', () => {
  it('los tres idiomas definen exactamente las mismas claves', () => {
    const base = aplanar(DICS.en);
    expect(base.length).toBeGreaterThan(200);
    for (const lang of IDIOMAS.slice(1)) {
      expect(aplanar(DICS[lang]), `claves distintas en ${lang}.json`).toEqual(base);
    }
  });

  it('ninguna traducción está vacía', () => {
    for (const lang of IDIOMAS) {
      const vacias = aplanar(DICS[lang]).filter((k) => {
        const v = valor(DICS[lang], k);
        return typeof v !== 'string' || v.trim() === '';
      });
      expect(vacias, `claves vacías en ${lang}.json`).toEqual([]);
    }
  });

  it('los parámetros {{...}} coinciden entre idiomas', () => {
    for (const clave of aplanar(DICS.en)) {
      const esperado = parametros(valor(DICS.en, clave) as string);
      if (esperado.length === 0) continue;
      for (const lang of IDIOMAS.slice(1)) {
        expect(parametros(valor(DICS[lang], clave) as string), `${clave} en ${lang}`)
          .toEqual(esperado);
      }
    }
  });
});

describe('i18n — el servicio traduce', () => {
  let i18n: I18nService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    i18n = TestBed.inject(I18nService);
    (i18n as unknown as { _translations: Record<string, unknown> })['_translations'] = DICS;
  });

  it('arranca en inglés y cambia de idioma', () => {
    expect(i18n.currentLang()).toBe('en');
    i18n.setLang('es');
    expect(i18n.currentLang()).toBe('es');
    expect(i18n.langLabel()).toBe('Español');
  });

  it('traduce con el diccionario del idioma activo', () => {
    i18n.setLang('es');
    expect(i18n.t('nav.poker')).toBe('Póker');
    i18n.setLang('en');
    expect(i18n.t('nav.poker')).toBe('Poker');
  });

  it('interpola los parámetros {{...}}', () => {
    i18n.setLang('es');
    expect(i18n.t('notify.login.body', { email: 'ana@42.fr' }))
      .toBe('Sesión iniciada como ana@42.fr');
  });

  it('si falta una clave devuelve la clave, no un hueco', () => {
    expect(i18n.t('no.existe.esta.clave')).toBe('no.existe.esta.clave');
  });
});
