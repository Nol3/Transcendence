// Configuración de ESLint (formato plano, ESLint 9) para el frontend Angular.
// Ver ROADMAP 2.4: se busca un lint útil y sin ruido, igual que `ruff` en el backend.
const eslint = require('@eslint/js');
const tseslint = require('typescript-eslint');
const angular = require('angular-eslint');

module.exports = tseslint.config(
  {
    // `qrcodegen.ts` es código de terceros (Project Nayuki, MIT) tal cual: se vendoriza sin tocar
    // su estilo, así que no se le pasa el linter.
    ignores: [
      'dist/**',
      '.angular/**',
      'node_modules/**',
      'playwright-report/**',
      'test-results/**',
      'src/app/shared/qr/qrcodegen.ts',
    ],
  },
  {
    files: ['**/*.ts'],
    extends: [
      eslint.configs.recommended,
      ...tseslint.configs.recommended,
      ...angular.configs.tsRecommended,
    ],
    processor: angular.processInlineTemplates,
    rules: {
      // El proyecto usa `any` puntualmente al leer mensajes de WebSocket.
      '@typescript-eslint/no-explicit-any': 'off',
      // Los componentes declaran selectores con prefijo `app-`.
      '@angular-eslint/component-selector': [
        'error',
        { type: 'element', prefix: 'app', style: 'kebab-case' },
      ],
      '@angular-eslint/directive-selector': [
        'error',
        { type: 'attribute', prefix: 'app', style: 'camelCase' },
      ],
      // Los tests de e2e y los mocks usan parámetros que no se leen.
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
    },
  },
  {
    files: ['**/*.html'],
    extends: [...angular.configs.templateRecommended],
    rules: {},
  },
);
