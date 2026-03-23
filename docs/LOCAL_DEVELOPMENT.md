# Local Development Setup (Without Docker)

This guide helps you set up the project locally for faster development iterations.

## ⚠️ Prerequisites

- **Python 3.11+** - [Download](https://www.python.org/downloads/)
- **Node.js 18+** - [Download](https://nodejs.org/)
- **SQLite3** (usually comes with Python)

## 🔧 Backend Setup (Django)

### Step 1: Create Virtual Environment

```bash
cd backend
python -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate
```

### Step 2: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3: Database Setup

```bash
# Run migrations
python manage.py migrate

# Create superuser (admin)
python manage.py createsuperuser
# Follow prompts:
# Username: admin
# Email: admin@example.com
# Password: ****

# (Optional) Load sample data
python manage.py shell < ../docs/sample_data.py
```

### Step 4: Run Development Server

```bash
python manage.py runserver 0.0.0.0:8000
```

Backend runs at: **http://localhost:8000**
Admin panel: **http://localhost:8000/admin**

### Useful Django Commands

```bash
# Create new app
python manage.py startapp appname apps/appname

# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Access Django shell
python manage.py shell

# Run tests
python manage.py test

# Clear database
python manage.py flush

# Create cache table (for sessions)
python manage.py createcachetable
```

## 🎨 Frontend Setup (Angular)

### Step 1: Install Dependencies

```bash
cd frontend
npm install
```

### Step 2: Start Development Server

```bash
npm start
# or
ng serve
```

Frontend runs at: **http://localhost:4200**

### Development Server Options

```bash
# Standard dev server
npm start

# With live reload on every file change
ng serve --poll 2000

# On specific port
ng serve --port 3000

# For all network interfaces
ng serve --host 0.0.0.0
```

### Useful Angular Commands

```bash
# Generate component
ng generate component modules/auth/components/login
# Shorthand:
ng g c modules/auth/components/login

# Generate service
ng generate service services/my-service
ng g s services/my-service

# Generate module
ng generate module modules/my-feature

# Build project
ng build

# Run tests
ng test

# Run linter
ng lint

# See available schematics
ng config defaults.schematics
```

## 🔌 CORS Configuration

Since you're running frontend and backend on **different ports** locally, you need CORS enabled.

When running locally:
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:4200`

Update `.env`:
```env
CORS_ALLOWED_ORIGINS=http://localhost:4200,http://localhost:3000,http://127.0.0.1:4200
```

## 🔐 Authentication (JWT)

The backend generates JWT tokens. The frontend needs to:

1. **Store token** in localStorage or sessionStorage:
```typescript
// In auth.service.ts after login
localStorage.setItem('access_token', response.token);
```

2. **Include token** in API requests:
```typescript
// Create an HTTP interceptor
import { HttpInterceptor, HttpRequest, HttpHandler, HttpEvent } from '@angular/common/http';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {
  constructor(private authService: AuthService) {}

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    const token = localStorage.getItem('access_token');
    if (token) {
      req = req.clone({
        setHeaders: {
          Authorization: `Bearer ${token}`
        }
      });
    }
    return next.handle(req);
  }
}

// Add to app.config.ts
import { HTTP_INTERCEPTORS } from '@angular/common/http';

export const appConfig: ApplicationConfig = {
  providers: [
    // ...
    {
      provide: HTTP_INTERCEPTORS,
      useClass: AuthInterceptor,
      multi: true
    }
  ]
};
```

## 📡 API Testing

### Using cURL

```bash
# Register user
curl -X POST http://localhost:8000/api/users/register/ \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"testpass123"}'

# Login
curl -X POST http://localhost:8000/api/users/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass123"}'

# Get current user (with token)
curl -X GET http://localhost:8000/api/users/me/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# Health check
curl http://localhost:8000/api/health/
```

### Using VS Code REST Client Extension

Create a `requests.rest` file:
```
### Register
POST http://localhost:8000/api/users/register/
Content-Type: application/json

{
  "username": "testuser",
  "email": "test@example.com",
  "password": "testpass123"
}

### Get user (replace TOKEN)
GET http://localhost:8000/api/users/me/
Authorization: Bearer TOKEN

### Health check
GET http://localhost:8000/api/health/
```

Right-click and select "Send Request"

### Using Postman

1. Install [Postman](https://www.postman.com/downloads/)
2. Create requests for each endpoint
3. Use "Pre-request Script" to handle tokens automatically

## 🔍 Debugging

### Backend Debugging

```python
# Add print statements
print(f"User created: {user.username}")

# Use pdb (Python Debugger)
import pdb; pdb.set_trace()
# Then use: n (next), c (continue), l (list), p variable

# Or use ipython for better shell
pip install ipython
python manage.py shell_plus  # Best Django shell (requires django-extensions)
```

### Frontend Debugging

```typescript
// Console logging
console.log('User:', this.user);
console.table(this.users);

// Browser DevTools
// 1. Open browser DevTools (F12)
// 2. Go to Sources tab
// 3. Click on component file
// 4. Add breakpoints by clicking line numbers
// 5. Reload page to hit breakpoint

// Or in code:
debugger;  // Pauses execution when DevTools is open
```

## 📦 Dependency Management

### Backend

```bash
# Add new package
pip install package-name
pip install package-name==1.2.3  # Specific version

# Update requirements.txt
pip freeze > requirements.txt

# Uninstall package
pip uninstall package-name
```

### Frontend

```bash
# Add new package
npm install package-name
npm install --save-dev package-name  # Dev only

# Update package.json and package-lock.json
npm update

# Uninstall package
npm uninstall package-name
```

## 🧪 Running Tests Locally

### Backend Tests

```bash
cd backend
source .venv/bin/activate

# Run all tests
python manage.py test

# Run specific app
python manage.py test apps.users

# Run with verbose output
python manage.py test --verbosity=2

# Run specific test class
python manage.py test apps.users.tests.UserTests

# With coverage
pip install coverage
coverage run --source='apps' manage.py test
coverage report
coverage html  # Creates htmlcov/index.html
```

### Frontend Tests

```bash
cd frontend

# Run tests once
npm test -- --watch=false

# Run with watch
npm test

# With coverage
npm test -- --code-coverage
```

## 💾 Database Management

### View SQLite Database

```bash
cd backend

# Interactive SQLite shell
sqlite3 db.sqlite3

# Common SQL commands
sqlite> .tables                    # List all tables
sqlite> .schema auth_user          # View table structure
sqlite> SELECT * FROM auth_user;   # View all users
sqlite> SELECT COUNT(*) FROM auth_user;  # Count users
sqlite> .quit                      # Exit

# Or use a GUI tool
# - DB Browser for SQLite (https://sqlitebrowser.org/)
# - DBeaver (https://dbeaver.io/)
```

### Reset Database

```bash
# Option 1: Delete and recreate
rm db.sqlite3
python manage.py migrate

# Option 2: Flush data but keep structure
python manage.py flush

# Option 3: Start fresh with sample data
python manage.py flush --no-input
python manage.py migrate
python manage.py createsuperuser
```

## 🌐 Environment Variables for Local Development

Create `.env` in root:

```env
# Backend
DEBUG=true
DJANGO_DEBUG=true
DJANGO_SECRET_KEY=dev-secret-key-not-for-production
JWT_SECRET_KEY=dev-jwt-secret-key
CORS_ALLOWED_ORIGINS=http://localhost:4200,http://127.0.0.1:4200,http://localhost:3000

# Database
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3

# Frontend
NG_ENV=development
BACKEND_URL=http://localhost:8000
```

## 🚨 Common Issues & Solutions

### Issue: ModuleNotFoundError: No module named 'django'

**Solution:**
```bash
# Ensure venv is activated
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows

# Reinstall
pip install -r requirements.txt
```

### Issue: Port already in use

```bash
# Find what's using the port
lsof -i :8000   # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill the process
kill -9 <PID>   # macOS/Linux
taskkill /F /PID <PID>  # Windows

# Or use different port
python manage.py runserver 0.0.0.0:9000
ng serve --port 5000
```

### Issue: CORS errors in browser

**Solution:** Make sure backend is running and CORS_ALLOWED_ORIGINS includes your frontend URL

```env
CORS_ALLOWED_ORIGINS=http://localhost:4200
```

### Issue: Node modules issues

```bash
# Clear cache and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
```

## 📚 Development Workflow

1. **Backend development** — Work in `backend/` with Django server running
2. **Frontend development** — Work in `frontend/` with Angular dev server running
3. **Terminal setup** — Open 3 terminals:
   - Terminal 1: `cd backend && source .venv/bin/activate && python manage.py runserver`
   - Terminal 2: `cd frontend && npm start`
   - Terminal 3: For git, file editing, etc.

## 🚀 When Ready to Test With Docker

Once local development is complete, test with Docker:

```bash
# Go to project root
cd ..

# Build and run with Docker
docker compose up --build

# This ensures it works like in production
```

---

**Happy local development! 🎉**
