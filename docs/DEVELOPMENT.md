# Development Guide

## 📋 Project Structure

```
ft_transcendence/
├── frontend/              # Angular frontend application
│   ├── src/              # Source code
│   │   ├── app/          # Application code
│   │   │   ├── modules/  # Feature modules (games, chat, etc.)
│   │   │   ├── shared/   # Shared components, pipes, directives
│   │   │   ├── services/ # HTTP services (auth, game, etc.)
│   │   │   └── models/   # TypeScript interfaces
│   │   └── assets/       # Static assets
│   ├── package.json      # Dependencies
│   └── angular.json      # Angular configuration
├── backend/               # Django backend application
│   ├── config/           # Django project settings
│   ├── apps/             # Django applications
│   │   ├── users/        # User management
│   │   ├── games/        # Game logic
│   │   ├── chat/         # Chat functionality
│   │   └── tournament/   # Tournament management
│   ├── manage.py         # Django management script
│   └── requirements.txt   # Python dependencies
├── docker/                # Docker configuration
│   ├── Dockerfile.backend # Backend container
│   ├── Dockerfile.frontend # Frontend container
│   ├── nginx.conf         # Nginx reverse proxy config
│   ├── nginx-app.conf     # Nginx app config
│   ├── generate-ssl.sh    # SSL certificate generation
│   └── ssl/              # SSL certificates (generated)
├── docker-compose.yml     # Docker orchestration
├── .env.example          # Environment variables template
└── README.md             # Main documentation
```

## 🚀 Getting Started

### Prerequisites
- Docker (≥ 24.x)
- Docker Compose (≥ 2.x)
- Git

### Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone <repo-url> ft_transcendence
   cd ft_transcendence
   ```

2. **Initialize environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings if needed
   ```

3. **Generate SSL certificates:**
   ```bash
   chmod +x docker/generate-ssl.sh
   docker/generate-ssl.sh
   ```

4. **Build and start services:**
   ```bash
   docker compose up --build
   ```

5. **Access the application:**
   - Frontend: https://localhost:4200
   - Backend API: https://localhost:8000
   - Django Admin: https://localhost:8000/admin (username: admin, password: admin)

### Stopping Services
```bash
docker compose down
# To also remove volumes (wipes database):
docker compose down -v
```

## 🏗️ Architecture

### Services

#### Frontend (Angular 18)
- **Port:** 4200 (dev), served via Nginx in production
- **Framework:** Angular 18 with standalone components
- **Styling:** Bootstrap 5 + SCSS
- **State Management:** RxJS Observables
- **HTTP Client:** Angular HttpClient

#### Backend (Django + FastAPI)
- **Port:** 8000
- **Framework:** Django 4.2 LTS
- **API:** Django REST Framework
- **Database:** SQLite (development), PostgreSQL (production-ready config)
- **Authentication:** JWT via djangorestframework-simplejwt
- **WebSockets:** Daphne + Django Channels (for real-time features)

#### Database
- **Development:** SQLite3 (zero-config, file-based)
- **Volume:** `./backend/db.sqlite3` (persists between sessions)

#### Reverse Proxy (Nginx)
- **HTTPS:** Self-signed certificates (development)
- **Routes:**
  - `/` → Frontend
  - `/api/` → Backend API
  - `/admin/` → Django admin panel
  - `/static/` → Static files
  - `/media/` → Media files

## 👥 Team Workflow

Each team member should focus on their assigned module:

### Backend Modules (Django Apps)
- **pjimenez** → `apps/users` - User authentication & profiles
- **ribana-b** → `apps/games` - Game logic & mechanics
- **alcarden** → `apps/chat` - Real-time chat
- **jjaen-mo** → `apps/tournament` - Tournament management

### Frontend Modules (Angular)
- Create feature modules in `frontend/src/app/modules/`
- Use the service structure in `frontend/src/app/services/`
- Define models/interfaces in `frontend/src/app/models/`

## 🔧 Development Workflow

### Backend Development

1. **Navigate to backend:**
   ```bash
   cd backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

5. **Create superuser:**
   ```bash
   python manage.py createsuperuser
   ```

6. **Run development server:**
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

### Frontend Development

1. **Navigate to frontend:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Run Angular dev server:**
   ```bash
   npm start
   ```
   This serves at http://localhost:4200

4. **Build for production:**
   ```bash
   npm run build
   ```

## 📡 API Endpoints

### Users
- `POST /api/users/register/` - Register new user
- `POST /api/users/login/` - User login
- `GET /api/users/me/` - Get current user
- `GET /api/users/{id}/` - Get user profile

### Games
- `GET /api/games/` - List all games
- `GET /api/games/my_games/` - Get user's games
- `POST /api/games/create_game/` - Create new game
- `PATCH /api/games/{id}/` - Update game score

### Chat
- `GET /api/chat/messages/` - Get messages
- `POST /api/chat/messages/send_message/` - Send message
- `GET /api/chat/messages/conversation/` - Get conversation with user

### Tournament
- `GET /api/tournament/` - List tournaments
- `POST /api/tournament/create_tournament/` - Create tournament
- `POST /api/tournament/{id}/join/` - Join tournament
- `POST /api/tournament/{id}/leave/` - Leave tournament

### Health Check
- `GET /api/health/` - Backend health status

## 🔐 Environment Variables

See `.env.example` for all available variables. Key ones:

- `DJANGO_SECRET_KEY` - Secret key for Django
- `DJANGO_DEBUG` - Debug mode (true for development)
- `JWT_SECRET_KEY` - JWT signing key
- `CORS_ALLOWED_ORIGINS` - Allowed front-end origins
- `DATABASE_*` - Database configuration

## 🧪 Testing

### Backend Tests
```bash
cd backend
python manage.py test
```

### Frontend Tests
```bash
cd frontend
npm test
```

## 📝 Git Workflow

1. Create feature branches from `dev`:
   ```bash
   git checkout -b feature/your-feature
   ```

2. Commit with clear messages:
   ```bash
   git commit -m "feat: add user authentication"
   ```

3. Push and create pull request:
   ```bash
   git push origin feature/your-feature
   ```

4. Merge after code review to `dev`, then to `main`

## 🚨 Troubleshooting

### Docker Issues
- **Port already in use:** Change port in `docker-compose.yml`
- **Permission denied (SSL):** `chmod +x docker/generate-ssl.sh`
- **Database locked:** Run `docker compose down -v && docker compose up --build`

### Backend Issues
- **ModuleNotFoundError:** Ensure all imports are in `__init__.py`
- **CORS errors:** Check `CORS_ALLOWED_ORIGINS` in `.env`
- **Migration errors:** Run `python manage.py makemigrations` then `migrate`

### Frontend Issues
- **Port 4200 in use:** Change Angular dev server port in `angular.json`
- **Module not found:** Clear `node_modules` and run `npm install`
- **HTTPS error:** Make sure backend is accessible at configured URL

## 📚 Resources

- [Angular Documentation](https://angular.io/docs)
- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Docker Documentation](https://docs.docker.com/)
- [Bootstrap 5](https://getbootstrap.com/docs/5.0/)

## ✅ Checklist for Each Team Member

- [ ] Clone repository and complete initial setup
- [ ] Understand project structure and your assigned module
- [ ] Read API endpoints relevant to your work
- [ ] Set up development environment (backend or frontend)
- [ ] Create feature branch for your work
- [ ] Keep pushing commits regularly
- [ ] Create PRs for code review before merging
- [ ] Test your module locally with `docker compose up`
- [ ] Ensure no console errors in browser and backend logs

---

**Questions?** Check the main README.md or contact the project manager (@pjimenez).
