import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet],
  template: `
    <nav class="navbar navbar-expand-lg navbar-dark">
      <div class="container-fluid">
        <a class="navbar-brand" href="/">🎮 FT Transcendence</a>
      </div>
    </nav>

    <main class="main-container container-fluid">
      <router-outlet></router-outlet>
    </main>

    <footer>
      <p>&copy; 2026 FT Transcendence - 42 Project</p>
    </footer>
  `,
  styles: [`
    :host {
      display: flex;
      flex-direction: column;
      min-height: 100vh;
    }

    .main-container {
      flex: 1;
      padding: 2rem 1rem;
    }

    footer {
      margin-top: auto;
    }
  `]
})
export class AppComponent implements OnInit {
  title = 'FT Transcendence';

  ngOnInit() {
    console.log('FT Transcendence app initialized');
  }
}
