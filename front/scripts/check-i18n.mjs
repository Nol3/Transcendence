#!/usr/bin/env node
/**
 * Comprueba el estado del i18n del frontend:
 *
 *  1. que `en`, `es` y `fr` tengan exactamente las mismas claves;
 *  2. que ninguna traducción esté vacía y que los `{{parámetros}}` coincidan;
 *  3. que ninguna plantilla tenga texto visible sin pasar por el pipe `translate`.
 *
 * Uso: `npm run i18n:check` (devuelve 1 si algo falla, para que valga en CI).
 */
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';

const RAIZ = process.cwd();
const IDIOMAS = ['en', 'es', 'fr'];

/** Texto que no se traduce a propósito: logo partido, puntos de contraseña y nombres propios. */
const PERMITIDOS = [
  /^TRANS$/, /^CENDENCE$/, /^•+$/, /^GitHub$/, /^Discord$/,
  /^placeholder="•+"$/, /^aria-label="(GitHub|Discord)"$/,
];

const errores = [];

function aplanar(d, prefijo = '') {
  const claves = [];
  for (const [k, v] of Object.entries(d)) {
    if (v && typeof v === 'object') claves.push(...aplanar(v, `${prefijo}${k}.`));
    else claves.push(`${prefijo}${k}`);
  }
  return claves.sort();
}

function valor(d, clave) {
  let v = d;
  for (const p of clave.split('.')) v = v?.[p];
  return v;
}

function ficheros(dir, ext) {
  const salida = [];
  for (const e of readdirSync(dir)) {
    const p = join(dir, e);
    if (statSync(p).isDirectory()) salida.push(...ficheros(p, ext));
    else if (p.endsWith(ext) && !p.endsWith('.spec.ts')) salida.push(p);
  }
  return salida;
}

// ── 1 y 2: diccionarios ────────────────────────────────────────────────────
const dics = {};
for (const lang of IDIOMAS) {
  dics[lang] = JSON.parse(readFileSync(join(RAIZ, 'public', 'i18n', `${lang}.json`), 'utf8'));
}

const base = aplanar(dics.en);
for (const lang of IDIOMAS.slice(1)) {
  const otras = aplanar(dics[lang]);
  const faltan = base.filter((k) => !otras.includes(k));
  const sobran = otras.filter((k) => !base.includes(k));
  if (faltan.length) errores.push(`${lang}.json: faltan ${faltan.length} claves → ${faltan.slice(0, 5)}`);
  if (sobran.length) errores.push(`${lang}.json: sobran ${sobran.length} claves → ${sobran.slice(0, 5)}`);
}

const params = (s) => (s.match(/\{\{\w+\}\}/g) ?? []).sort().join(',');
for (const clave of base) {
  for (const lang of IDIOMAS) {
    const v = valor(dics[lang], clave);
    if (typeof v !== 'string' || !v.trim()) errores.push(`${lang}.json: «${clave}» vacía`);
    else if (params(v) !== params(valor(dics.en, clave))) {
      errores.push(`${lang}.json: «${clave}» tiene otros {{parámetros}} que en.json`);
    }
  }
}

// ── 3: plantillas ──────────────────────────────────────────────────────────
const texto = />\s*([A-Za-zÁÉÍÓÚáéíóúÑñ¿¡][^<>{}\n]{2,60})\s*</;
const atributo = /(placeholder|title|aria-label)="([^"{][^"]{2,60})"/;

for (const f of ficheros(join(RAIZ, 'src', 'app'), '.html')) {
  const rel = relative(RAIZ, f).replace(/\\/g, '/');
  readFileSync(f, 'utf8').split('\n').forEach((linea, i) => {
    if (linea.includes('| translate')) return;
    const t = texto.exec(linea);
    if (t && !PERMITIDOS.some((p) => p.test(t[1].trim()))) {
      errores.push(`${rel}:${i + 1} texto sin traducir → «${t[1].trim()}»`);
    }
    const a = atributo.exec(linea);
    if (a && !PERMITIDOS.some((p) => p.test(`${a[1]}="${a[2]}"`))) {
      errores.push(`${rel}:${i + 1} atributo sin traducir → ${a[1]}="${a[2]}"`);
    }
  });
}

// ── informe ────────────────────────────────────────────────────────────────
if (errores.length) {
  console.error(`✗ i18n: ${errores.length} problema(s)\n`);
  for (const e of errores) console.error('  ·', e);
  process.exit(1);
}

console.log(`✓ i18n: ${base.length} claves en ${IDIOMAS.join('/')}, sin literales sueltos en las plantillas`);
