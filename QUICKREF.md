# FT Transcendence - Quick Command Reference

## 🚀 Getting Started

```bash
# First time setup (runs everything automatically)
chmod +x setup.sh
./setup.sh

# Or manual setup
cp .env.example .env
docker/generate-ssl.sh
docker compose up --build
```

## 🐳 Docker Commands

```bash
# Start services
docker compose up                 # Foreground
docker compose up -d              # Background
docker compose up --build         # Rebuild images
docker compose up -d --build      # Background rebuild

# Stop services
docker compose down               # Stop containers
docker compose down -v            # Stop and remove volumes (wipes DB)
docker compose stop               # Stop without removing
docker compose restart            # Restart containers

# View logs
docker compose logs               # All services
docker compose logs -f            # Follow logs
docker compose logs backend       # Specific service
docker compose logs backend -f    # Follow specific service

# Access containers
docker compose exec backend sh    # Shell into backend
docker compose exec frontend sh   # Shell into frontend
docker exec ft_transcendence_backend python manage.py shell  # Django shell
```

## 🔧 Backend (Django)

```bash
# Navigate to backend
cd backend

# Setup (local development without Docker)
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser

# Running (Docker container)
docker compose exec backend python manage.py runserver 0.0.0.0:8000

# Database migrations
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py migrate apps.users

# Create data
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py shell

# Testing
python manage.py test
python manage.py test apps.users
pytest

# Django admin
# http://localhost:8000/admin
```

## 🎨 Frontend (Angular)

```bash
# Navigate to frontend
cd frontend

# Setup (local development without Docker)
npm install
npm start           # Runs on http://localhost:4200

# Building
npm run build               # Development build
npm run build -- --configuration production  # Production build
npm run watch              # Watch mode

# Testing
npm test
npm test -- --watch
ng test --code-coverage

# Linting
ng lint
```

## 📝 Git Workflow

```bash
# Check status
git status
git log --oneline -10        # Last 10 commits

# Create feature branch
git checkout -b feature/your-feature
git checkout -b bugfix/your-bug
git checkout -b docs/your-doc

# Make changes and commit
git add .
git commit -m "feat: description of feature"
git commit -amend              # Fix last commit

# Push and create PR
git push origin feature/your-feature

# Update from main/dev
git fetch origin
git rebase origin/dev          # Keep history clean
git pull origin dev            # Alternative: merge instead

# Switch branches
git checkout dev
git checkout main
```

## 🔐 Environment & Configuration

```bash
# View environment variables
cat .env
cat .env.example        # See available vars

# Update .env
# Edit with your editor, important variables:
DJANGO_SECRET_KEY=...
JWT_SECRET_KEY=...
DJANGO_DEBUG=false      # For production
```

## 🧪 Testing

```bash
# Backend tests
cd backend
python manage.py test

# Frontend tests
cd frontend
npm test

# Test specific app/module
python manage.py test apps.users
npm test -- --include="**/auth/**"

# With coverage
pip install coverage
coverage run --source='.' manage.py test
coverage report
coverage html  # Generate HTML report
```

## 🔍 Debugging

```bash
# Backend logs
docker compose logs -f backend

# Frontend logs
docker compose logs -f frontend

# Django shell
docker compose exec backend python manage.py shell
>>> from django.contrib.auth.models import User
>>> User.objects.all()

# Nginx logs
docker compose logs -f nginx

# Check specific endpoint
curl -H "Authorization: Bearer TOKEN" https://localhost:8000/api/users/me/

# Check all running containers
docker compose ps
```

## 📊 Database

```bash
# Backup database
docker compose exec backend cp db.sqlite3 db.sqlite3.backup

# Reset database
docker compose down -v              # Remove volume
docker compose up -d               # Recreate fresh
docker compose exec backend python manage.py migrate

# Access database directly
docker compose exec backend sqlite3 db.sqlite3
> .tables
> SELECT * FROM auth_user;
> .exit
```

## 🚨 Troubleshooting

```bash
# Port already in use
# Edit docker-compose.yml: change port mapping
# Or kill process: lsof -i :8000 | kill -9 <PID>

# Database locked
docker compose down -v
docker compose up --build

# Module not found (Python)
docker compose exec backend pip install -r requirements.txt

# Module not found (Node)
docker compose exec frontend npm install

# Clear node modules
cd frontend
rm -rf node_modules
npm install

# Clear Python cache
find backend -type d -name __pycache__ -exec rm -r {} +
find backend -name "*.pyc" -delete
```

## 📱 Testing Responsive Design

```bash
# In browser DevTools (Chrome/Firefox):
# 1. Press F12
# 2. Click "Toggle Device Toolbar" (Ctrl+Shift+M)
# 3. Test on: 375px (mobile), 768px (tablet), 1200px+ (desktop)

# Command line testing
curl -A "Mobile Safari" https://localhost:4200
```

## 🔑 Default Credentials (Development Only)

```
Admin User:
  Username: admin
  Password: admin
  URL: https://localhost:8000/admin

Test User (create with):
  python manage.py createsuperuser
```

## 📚 Useful Links

- Django Admin: https://localhost:8000/admin
- Frontend App: https://localhost:4200
- Backend API: https://localhost:8000/api/
- API Health: https://localhost:8000/api/health/
- Nginx: https://localhost (reverse proxy)

## 💡 Pro Tips

```bash
# Combine commands
docker compose exec backend python manage.py migrate && python manage.py runserver

# Run command in background
docker compose exec -d backend python manage.py runserver

# Don't recreate containers
docker compose up --no-recreate

# Build specific service
docker compose build backend
docker compose build frontend

# Check container IP
docker compose exec backend hostname -I

# View Docker resource usage
docker stats

# Clean up unused Docker resources
docker system prune -a
```

## 📖 Full Documentation

- **Setup & Development:** docs/DEVELOPMENT.md
- **Contributing Guidelines:** CONTRIBUTING.md
- **Backend Documentation:** backend/README.md
- **Frontend Documentation:** frontend/README.md

---

**For more details, see the full documentation files above! 🚀**
