import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

import { qrcodegen } from './qrcodegen';

/**
 * Un QR que se pinta **en el cliente**: ni el código de la sala ni el enlace salen a ningún
 * servicio de terceros. El codificador es el de Project Nayuki (MIT, ver `qrcodegen.ts`).
 *
 * Se dibuja como SVG con un solo `<path>`, no con 800 `<rect>`: pesa menos y se ve nítido en
 * cualquier tamaño. `shape-rendering="crispEdges"` evita el difuminado entre módulos, que es lo que
 * hace que un lector no lo pille.
 */
@Component({
  selector: 'app-qr-sala',
  template: `
    <svg
      class="qr"
      [attr.viewBox]="'0 0 ' + lado() + ' ' + lado()"
      [attr.width]="tam()"
      [attr.height]="tam()"
      shape-rendering="crispEdges"
      role="img"
      [attr.aria-label]="etiqueta()"
    >
      <rect [attr.width]="lado()" [attr.height]="lado()" fill="#ffffff" />
      <path [attr.d]="dibujo()" fill="#000000" />
    </svg>
  `,
  styles: `
    :host {
      display: inline-block;
      line-height: 0;
    }
    .qr {
      border-radius: 8px;
      background: #fff;
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class QrSala {
  /** Lo que se codifica: normalmente el enlace para entrar en la sala. */
  readonly texto = input.required<string>();
  /** Texto accesible del QR (el enlace no se lee bien en voz alta, así que se describe). */
  readonly etiqueta = input('QR para entrar en la sala');
  /** Tamaño en píxeles del lado. */
  readonly tam = input(200);

  private readonly codigo = computed(() => qrcodegen.QrCode.encodeText(this.texto(), qrcodegen.QrCode.Ecc.MEDIUM));

  readonly lado = computed(() => this.codigo().size + 2 * 4);

  /** Un solo trazado con todos los módulos oscuros, con el margen blanco reglamentario (4 módulos). */
  readonly dibujo = computed(() => {
    const qr = this.codigo();
    const partes: string[] = [];
    for (let y = 0; y < qr.size; y++) {
      for (let x = 0; x < qr.size; x++) {
        if (qr.getModule(x, y)) partes.push(`M${x + 4},${y + 4}h1v1h-1z`);
      }
    }
    return partes.join('');
  });
}
