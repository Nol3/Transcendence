import {
  ChangeDetectionStrategy,
  Component,
  OnDestroy,
  computed,
  input,
  output,
  signal,
} from '@angular/core';

import { PlayingCard } from '../../../../shared/components/playing-card/playing-card';
import { TranslatePipe } from '../../../../i18n';
import { PokerHandReplay } from '../../../../core/services/poker-history.service';

/** Un renglón del registro de jugadas, ya listo para pintar. */
interface Linea {
  seat: number | null;
  nombre: string;
  clave: string;          // clave de traducción
  params: Record<string, string | number>;
}

/**
 * Replay de una mano (roadmap 7.2): reproduce paso a paso lo que pasó.
 *
 * Se apoya en el registro de acciones que guarda el motor (`hand_start`, `blind`,
 * `action`, `street`, `hand_end`). Todo lo que se ve —tablero, bote, quién se retiró—
 * se **reconstruye** recorriendo los pasos hasta el actual, así que el componente no
 * guarda estado del juego: solo un número de paso.
 */
@Component({
  selector: 'app-hand-replay',
  imports: [PlayingCard, TranslatePipe],
  templateUrl: './hand-replay.html',
  styleUrl: './hand-replay.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HandReplay implements OnDestroy {
  readonly hand = input.required<PokerHandReplay>();
  readonly closed = output<void>();

  readonly step = signal(0);
  readonly playing = signal(false);
  private timer: ReturnType<typeof setInterval> | null = null;

  readonly total = computed(() => this.hand().actions?.length ?? 0);
  readonly actual = computed(() => Math.min(this.step(), Math.max(0, this.total() - 1)));

  /** Lo que se ve en el paso actual, reconstruido desde el registro. */
  readonly vista = computed(() => {
    const mano = this.hand();
    const acciones = mano.actions ?? [];
    const hasta = this.actual();

    let board: string[] = [];
    let bote = 0;
    let turno: number | null = null;
    let calle = 'preflop';
    const retirados = new Set<number>();
    const lineas: Linea[] = [];
    const nombre = (seat: number | null | undefined) =>
      mano.players.find((p) => p.seat === seat)?.name ?? `#${seat}`;

    for (let i = 0; i <= hasta && i < acciones.length; i++) {
      const a = acciones[i];
      switch (a.event) {
        case 'hand_start':
          lineas.push({ seat: null, nombre: '', clave: 'replay.start', params: {} });
          break;
        case 'blind':
          bote += a.amount ?? 0;
          lineas.push({
            seat: a.seat ?? null, nombre: nombre(a.seat), clave: 'replay.blind',
            params: { kind: a.kind ?? '', amount: a.amount ?? 0 },
          });
          break;
        case 'action': {
          bote += a.amount ?? 0;
          turno = a.seat ?? null;
          calle = a.street ?? calle;
          if (a.action === 'fold') retirados.add(a.seat as number);
          lineas.push({
            seat: a.seat ?? null, nombre: nombre(a.seat), clave: `replay.act.${a.action}`,
            params: { amount: a.amount ?? 0 },
          });
          break;
        }
        case 'street':
          board = a.board ?? [];
          calle = a.street ?? calle;
          lineas.push({ seat: null, nombre: '', clave: `replay.street.${a.street}`, params: {} });
          break;
        case 'uncalled_return':
          bote -= a.amount ?? 0;
          break;
        case 'hand_end':
          lineas.push({
            seat: a.winner ?? null, nombre: nombre(a.winner), clave: 'replay.winner',
            params: { amount: a.amount ?? 0, name: nombre(a.winner) },
          });
          break;
      }
    }

    return { board, bote, turno, calle, retirados, lineas };
  });

  /** Cartas "7c 2s" → lista, para pintarlas una a una. */
  cards(field: string): string[] {
    return (field || '').split(/\s+/).filter(Boolean);
  }

  // ── Controles ────────────────────────────────────────────────────────────
  primero(): void { this.parar(); this.step.set(0); }
  anterior(): void { this.parar(); this.step.set(Math.max(0, this.actual() - 1)); }
  siguiente(): void { this.parar(); this.step.set(Math.min(this.total() - 1, this.actual() + 1)); }
  ultimo(): void { this.parar(); this.step.set(Math.max(0, this.total() - 1)); }

  reproducir(): void {
    if (this.playing()) { this.parar(); return; }
    if (this.actual() >= this.total() - 1) this.step.set(0);
    this.playing.set(true);
    this.timer = setInterval(() => {
      if (this.actual() >= this.total() - 1) { this.parar(); return; }
      this.step.update((s) => s + 1);
    }, 900);
  }

  ngOnDestroy(): void {
    // El intervalo se quedaba vivo si salías de la página a mitad de reproducción: seguía
    // avanzando el `step` de un componente que ya no existe.
    this.parar();
  }

  private parar(): void {
    this.playing.set(false);
    if (this.timer !== null) { clearInterval(this.timer); this.timer = null; }
  }

  cerrar(): void {
    this.parar();
    this.closed.emit();
  }
}
