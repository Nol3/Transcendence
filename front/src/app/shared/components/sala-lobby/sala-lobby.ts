import { ChangeDetectionStrategy, Component, computed, inject, input, output, signal } from '@angular/core';

import { TranslatePipe } from '../../../i18n';
import { SalaOnlineService } from '../../../core/services/sala-online.service';
import { ButtonComponent } from '../button/button';

/**
 * El lobby de una sala: crear una, entrar con un código y esperar a que se llene.
 *
 * Es **uno solo para todos los juegos**, porque el lobby es idéntico en todos: cambia el id del
 * juego y poco más. La pantalla de cada juego solo tiene que enseñarlo cuando el jugador elige
 * «con amigos», y ponerse a pintar la partida cuando `sala()` pase a `playing`.
 */
@Component({
  selector: 'app-sala-lobby',
  imports: [ButtonComponent, TranslatePipe],
  templateUrl: './sala-lobby.html',
  styleUrl: './sala-lobby.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SalaLobby {
  private readonly salas = inject(SalaOnlineService);

  /** El id del juego en el servidor (`mentiroso`, `brisca`, `tute`, `mus`…). */
  readonly juego = input.required<string>();
  /** Las opciones con las que se crea la sala. */
  readonly opciones = input<Record<string, unknown>>({});
  readonly minJugadores = input(2);
  readonly maxJugadores = input(6);
  readonly permiteBots = input(true);

  /** Salir del modo «con amigos» y volver al menú del juego. */
  readonly volver = output<void>();

  readonly connection = this.salas.connection;
  readonly sala = this.salas.sala;
  readonly error = this.salas.error;
  readonly errorTexto = this.salas.errorTexto;

  /** `menu` = crear o entrar; `sala` = ya dentro, esperando. */
  readonly paso = signal<'menu' | 'sala'>('menu');
  readonly codigo = signal('');
  readonly copiado = signal(false);
  readonly ocupado = signal(false);

  readonly puedeEmpezar = computed(() => {
    const s = this.sala();
    if (!s) return false;
    const conectados = s.players.filter((p) => p.connected).length;
    return s.isHost && conectados >= this.minJugadores();
  });

  readonly lleno = computed(() => (this.sala()?.players.length ?? 0) >= this.maxJugadores());

  /** El enlace para pasarle a un amigo, con el código dentro. */
  readonly enlace = computed(() => `${location.origin}${location.pathname}?codigo=${this.sala()?.code ?? ''}`);

  constructor() {
    // Si la pantalla llega con `?codigo=XXXX` (el enlace que se pasa un amigo), se entra directo.
    const enUrl = new URLSearchParams(location.search).get('codigo');
    if (enUrl) {
      this.codigo.set(enUrl.toUpperCase());
      void this.entrar();
    }
  }

  async crear(): Promise<void> {
    this.ocupado.set(true);
    this.salas.limpiarError();
    try {
      const code = await this.salas.crear(this.juego(), this.opciones());
      this.salas.conectar(this.juego(), code);
      this.paso.set('sala');
    } catch {
      this.error.set('sala.error.crear');
    } finally {
      this.ocupado.set(false);
    }
  }

  async entrar(): Promise<void> {
    const code = this.codigo().trim().toUpperCase();
    if (code.length < 4) {
      this.error.set('sala.error.codigo');
      return;
    }
    this.ocupado.set(true);
    this.salas.limpiarError();
    try {
      await this.salas.mirar(code);
      this.salas.conectar(this.juego(), code);
      this.paso.set('sala');
    } catch {
      this.error.set('sala.error.noExiste');
    } finally {
      this.ocupado.set(false);
    }
  }

  repartir(): void {
    this.salas.repartir();
  }

  anadirBot(): void {
    this.salas.anadirBot();
  }

  quitarBot(): void {
    this.salas.quitarBot();
  }

  /** Volver a entrar tras una caída. */
  reconectar(): void {
    const code = this.sala()?.code;
    if (code) this.salas.reconectar(code);
  }

  async copiarEnlace(): Promise<void> {
    try {
      await navigator.clipboard.writeText(this.enlace());
      this.copiado.set(true);
      setTimeout(() => this.copiado.set(false), 1500);
    } catch {
      this.copiado.set(false);
    }
  }

  salir(): void {
    this.salas.desconectar();
    this.paso.set('menu');
    this.codigo.set('');
    this.volver.emit();
  }
}
