# Frontend Documentation

## 📁 Project Structure

```
frontend/
├── src/
│   ├── index.html         # Main HTML entry point
│   ├── main.ts            # Bootstrap Angular application
│   ├── styles.scss        # Global styles
│   ├── favicon.ico        # App icon
│   └── app/
│       ├── app.component.ts      # Root component
│       ├── app.routes.ts         # Route definitions
│       ├── app.config.ts         # Angular app configuration
│       ├── modules/              # Feature modules
│       │   ├── auth/             # Authentication (login, register)
│       │   ├── games/            # Game components
│       │   ├── chat/             # Chat components
│       │   └── tournament/       # Tournament components
│       ├── shared/               # Reusable components
│       │   ├── components/       # Shared UI components (header, footer, etc.)
│       │   ├── pipes/            # Custom pipes
│       │   └── directives/       # Custom directives
│       ├── services/             # HTTP services
│       │   ├── auth.service.ts
│       │   ├── game.service.ts
│       │   ├── chat.service.ts
│       │   └── tournament.service.ts
│       └── models/               # TypeScript interfaces
│           └── index.ts          # All model interfaces
├── angular.json           # Angular configuration
├── tsconfig.json          # TypeScript configuration
├── package.json           # Dependencies
└── README.md             # This file
```

## 🔧 Technology Stack

- **Framework:** Angular 18 (standalone components)
- **Styling:** Bootstrap 5 + SCSS
- **HTTP Client:** Angular HttpClient
- **State Management:** RxJS Observables
- **Routing:** Angular Router
- **TypeScript:** v5.4

## 🎯 Module Structure

Each module should follow this pattern:

```
modules/
└── feature-name/
    ├── components/           # Module-specific components
    │   ├── list/
    │   │   ├── list.component.ts
    │   │   ├── list.component.html
    │   │   └── list.component.scss
    │   └── detail/
    │       ├── detail.component.ts
    │       ├── detail.component.html
    │       └── detail.component.scss
    ├── feature-name.module.ts (if needed)
    └── feature-name.routes.ts (if using lazy loading)
```

## 📦 Available Services

### AuthService
```typescript
// Login/Register
register(username: string, email: string, password: string): Observable<User>
login(username: string, password: string): Observable<any>
logout(): Observable<any>

// User data
getCurrentUser(): Observable<User>
```

### GameService
```typescript
getMyGames(): Observable<Game[]>
getGame(id: number): Observable<Game>
createGame(player2Id: number): Observable<Game>
updateGameScore(gameId: number, p1Score: number, p2Score: number): Observable<Game>
```

### ChatService (to implement)
```typescript
getMessages(): Observable<Message[]>
sendMessage(recipientId: number, content: string): Observable<Message>
getConversation(userId: number): Observable<Message[]>
```

### TournamentService (to implement)
```typescript
getTournaments(): Observable<Tournament[]>
createTournament(name: string, maxPlayers: number): Observable<Tournament>
joinTournament(id: number): Observable<void>
leaveTournament(id: number): Observable<void>
```

## 🏗️ Creating a New Component

### Step 1: Generate Component
```bash
ng generate component modules/feature-name/components/my-component
```

### Step 2: Define Component
```typescript
// my-component.component.ts
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { MyService } from '@services/my.service';

@Component({
  selector: 'app-my-component',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './my-component.component.html',
  styleUrls: ['./my-component.component.scss']
})
export class MyComponentComponent implements OnInit {
  data$ = this.service.getData();

  constructor(
    private service: MyService,
    private route: ActivatedRoute
  ) {}

  ngOnInit() {
    // Initialization logic
  }
}
```

### Step 3: Create Template
```html
<!-- my-component.component.html -->
<div class="container">
  <h1>My Component</h1>
  <div *ngFor="let item of (data$ | async) as items">
    {{ item.name }}
  </div>
</div>
```

### Step 4: Add Styles
```scss
// my-component.component.scss
.container {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}
```

## 🌐 API Integration

All services use Angular HttpClient to communicate with the backend:

```typescript
constructor(private http: HttpClient) {}

getUsers(): Observable<User[]> {
  return this.http.get<User[]>('/api/users/');
}

createGame(player2Id: number): Observable<Game> {
  return this.http.post<Game>('/api/games/create_game/', { player2_id: player2Id });
}
```

## 🔄 Routing

Routes are defined in `app.routes.ts`:

```typescript
export const routes: Routes = [
  {
    path: 'auth',
    loadComponent: () => import('./modules/auth/auth.component').then(m => m.AuthComponent)
  },
  {
    path: 'games',
    loadComponent: () => import('./modules/games/games.component').then(m => m.GamesComponent)
  },
  // Add more routes here
];
```

Usage in component:
```typescript
constructor(private router: Router) {}

navigateToGame(gameId: number) {
  this.router.navigate(['/games', gameId]);
}
```

## 🎨 Styling Guidelines

- Use **Bootstrap classes** for layout and common components
- Use **SCSS variables** for colors, spacing, fonts
- Define global styles in `styles.scss`
- Component-specific styles in component `.scss` files

### Global Style Variables
Configure in `src/styles.scss`:
```scss
// Colors
$primary-color: #007bff;
$secondary-color: #6c757d;
$danger-color: #dc3545;

// Spacing
$spacer: 1rem;

// Breakpoints
$sm: 576px;
$md: 768px;
$lg: 992px;
$xl: 1200px;
```

## 📱 Responsive Design

Use Bootstrap grid system:
```html
<div class="container">
  <div class="row">
    <div class="col-md-6 col-lg-4">
      <!-- Content adapts to screen size -->
    </div>
  </div>
</div>
```

Test responsive design:
```bash
# Chrome DevTools (F12) → Toggle device toolbar (Ctrl+Shift+M)
# Test on: mobile (375px), tablet (768px), desktop (1200px+)
```

## 🧪 Component Testing

Create tests alongside components:

```typescript
// my-component.component.spec.ts
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MyComponentComponent } from './my-component.component';

describe('MyComponentComponent', () => {
  let component: MyComponentComponent;
  let fixture: ComponentFixture<MyComponentComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MyComponentComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(MyComponentComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should display data', () => {
    component.data$ = of([{ name: 'Test' }]);
    fixture.detectChanges();
    const compiled = fixture.nativeElement;
    expect(compiled.querySelector('h1')).toBeTruthy();
  });
});
```

Run tests:
```bash
npm test
```

## 🚀 Building for Production

```bash
# Development build
npm run build

# Watch mode (rebuild on file changes)
npm run watch

# Production build (optimized)
npm run build -- --configuration production
```

## 🔒 Security

- ✅ Input validation on all forms
- ✅ XSS prevention (Angular sanitizes HTML)
- ✅ CSRF protection (Backend handles)
- ✅ Store JWT token securely
- ✅ Validate user permissions on frontend (backend enforces)

## ⚠️ Common Gotchas

### OnPush Change Detection
```typescript
@Component({
  selector: 'app-my',
  changeDetection: ChangeDetectionStrategy.OnPush,
  // Use this for better performance in large apps
})
```

### Unsubscribe to Prevent Memory Leaks
```typescript
private destroy$ = new Subject<void>();

ngOnInit() {
  this.service.getData()
    .pipe(takeUntil(this.destroy$))
    .subscribe(data => this.data = data);
}

ngOnDestroy() {
  this.destroy$.next();
  this.destroy$.complete();
}
```

### Use trackBy in *ngFor
```html
<div *ngFor="let item of items; trackBy: trackByFn">
  {{ item.name }}
</div>
```

```typescript
trackByFn(index: number, item: any) {
  return item.id;
}
```

## 📚 Resources

- [Angular Docs](https://angular.io/docs)
- [Bootstrap 5](https://getbootstrap.com/docs/5.0/)
- [RxJS Documentation](https://rxjs.dev/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)

## ✅ Before Committing

- [ ] All components compile: `npm run build`
- [ ] No console errors/warnings
- [ ] Tests pass: `npm test`
- [ ] Code formatted properly
- [ ] Components are documented
- [ ] Responsive design tested (mobile, tablet, desktop)

---

**Questions?** Check Angular docs or ask the team!
