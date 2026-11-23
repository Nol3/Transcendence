import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { Header } from './shared/components/header/header';
import { FooterComponent } from './shared/components/footer/footer';
import { ToastComponent } from './shared/components/toast/toast';
import { MotionService } from './core/ui/motion.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, Header, FooterComponent, ToastComponent],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  // Se instancia al arrancar para que la clase `reduce-motion` esté puesta antes de pintar.
  private readonly motion = inject(MotionService);
}
