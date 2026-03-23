# Backend API Documentation

## 📁 Project Structure

```
backend/
├── config/                 # Project configuration
│   ├── settings.py        # Django settings
│   ├── urls.py            # URL routing
│   ├── asgi.py            # ASGI configuration (WebSockets)
│   └── wsgi.py            # WSGI configuration (Production)
├── apps/                   # Django applications (microservices)
│   ├── users/             # User authentication & profiles
│   │   ├── models.py      # User & UserProfile models
│   │   ├── views.py       # API views
│   │   ├── serializers.py # Request/response serializers
│   │   ├── urls.py        # URL routes
│   │   └── admin.py       # Django admin config
│   ├── games/             # Game logic & history
│   ├── chat/              # Messaging system
│   └── tournament/        # Tournament management
├── static/                # Static files (CSS, images, etc.)
├── media/                 # User-uploaded files
├── db.sqlite3             # Database (development)
├── manage.py              # Django management script
└── requirements.txt       # Python dependencies
```

## 🔧 Technology Stack

- **Framework:** Django 4.2 LTS
- **API:** Django REST Framework 3.14
- **Database:** SQLite3 (dev) / PostgreSQL (production-ready)
- **Authentication:** JWT via djangorestframework-simplejwt
- **Real-time:** Daphne + Django Channels
- **CORS:** django-cors-headers

## 📚 Apps Overview

### Users App (`apps/users/`)
**Responsible for:** User authentication, profiles, user data

**Models:**
- `User` (Django built-in) - Username, email, password
- `UserProfile` - Extended user data (avatar, bio, stats, ELO rating)

**Key Endpoints:**
- `POST /api/users/register/` - Register new user
- `POST /api/users/login/` - Login (returns JWT token)
- `GET /api/users/me/` - Get current user
- `GET /api/users/{id}/` - Get user profile
- `PATCH /api/users/{id}/` - Update profile

**Developer:** pjimenez

---

### Games App (`apps/games/`)
**Responsible for:** Game creation, score tracking, game history

**Models:**
- `Game` - Records of played games (player1, player2, winner, score, status)

**Key Endpoints:**
- `GET /api/games/` - List all games
- `GET /api/games/my_games/` - Get user's game history
- `POST /api/games/create_game/` - Start new game
- `PATCH /api/games/{id}/` - Update game score
- `POST /api/games/{id}/finish/` - Mark game as finished

**Developer:** ribana-b

---

### Chat App (`apps/chat/`)
**Responsible for:** Messaging system, real-time communication

**Models:**
- `Message` - Individual messages between users

**Key Endpoints:**
- `GET /api/chat/messages/` - Get all messages for user
- `POST /api/chat/messages/send_message/` - Send new message
- `GET /api/chat/messages/conversation/?user_id=X` - Get conversation with user
- `PATCH /api/chat/messages/{id}/` - Mark as read
- `DELETE /api/chat/messages/{id}/` - Delete message

**Features:**
- Real-time messaging with WebSockets
- Read status tracking
- Message history

**Developer:** alcarden

---

### Tournament App (`apps/tournament/`)
**Responsible for:** Tournament creation, management, participant tracking

**Models:**
- `Tournament` - Tournament metadata (name, status, creator, max_players)
- `TournamentParticipant` - Links users to tournaments

**Key Endpoints:**
- `GET /api/tournament/` - List tournaments
- `POST /api/tournament/create_tournament/` - Create tournament
- `POST /api/tournament/{id}/join/` - Join tournament
- `POST /api/tournament/{id}/leave/` - Leave tournament
- `POST /api/tournament/{id}/start/` - Start tournament (only creator)
- `GET /api/tournament/{id}/matches/` - Get tournament bracket

**Developer:** jjaen-mo

---

## 🔄 Authentication Flow

1. **Register:** `POST /api/users/register/`
   - Receives: username, email, password
   - Returns: User object + JWT token

2. **Login:** `POST /api/users/login/`
   - Receives: username, password
   - Returns: JWT token (valid for 24 hours by default)

3. **Using Token:** Add to request header
   ```
   Authorization: Bearer <your-jwt-token>
   ```

4. **Refresh Token:** (to be implemented)
   - Extends session without re-login

5. **Logout:** `POST /api/users/logout/`
   - Invalidates token

## 📝 Adding New Endpoints

### Step 1: Define Model (if needed)
```python
# apps/mymodule/models.py
from django.db import models
from django.contrib.auth.models import User

class MyModel(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
```

### Step 2: Create Serializer
```python
# apps/mymodule/serializers.py
from rest_framework import serializers
from .models import MyModel

class MyModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyModel
        fields = ['id', 'name', 'created_at']
```

### Step 3: Create ViewSet
```python
# apps/mymodule/views.py
from rest_framework import viewsets
from .models import MyModel
from .serializers import MyModelSerializer

class MyModelViewSet(viewsets.ModelViewSet):
    queryset = MyModel.objects.all()
    serializer_class = MyModelSerializer
```

### Step 4: Register URLs
```python
# apps/mymodule/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'mymodels', views.MyModelViewSet, basename='mymodel')

urlpatterns = [
    path('', include(router.urls)),
]
```

### Step 5: Include in Main URLs
```python
# config/urls.py
urlpatterns += [
    path('api/mymodule/', include('apps.mymodule.urls', namespace='mymodule')),
]
```

## 🧪 Running Tests

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test apps.users

# Run with coverage
pip install coverage
coverage run --source='.' manage.py test
coverage report
```

## 🚀 Running Django Commands

```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser (admin)
python manage.py createsuperuser

# Create sample data
python manage.py shell
>>> from django.contrib.auth.models import User
>>> User.objects.create_user('testuser', 'test@example.com', 'password')
```

## 🔒 Security Best Practices

- ✅ Passwords are hashed + salted (Django built-in)
- ✅ CORS configured to only allow frontend origin
- ✅ HTTPS enforced (self-signed certs in dev, real certs in production)
- ✅ JWT tokens expire after 24 hours
- ✅ Sensitive data not exposed in API responses
- ✅ SQL injection prevented via ORM
- ✅ CSRF protection enabled

## 🐛 Debugging

### Enable Django Debug Toolbar
```bash
pip install django-debug-toolbar
# Add to INSTALLED_APPS in settings.py
```

### View SQL Queries
```python
from django.db import connection, reset_queries
from django.test.utils import override_settings

@override_settings(DEBUG=True)
def my_view():
    reset_queries()
    # ... your code ...
    for query in connection.queries:
        print(query['sql'])
```

### API Response Inspection
```bash
# Test endpoints with curl
curl -H "Authorization: Bearer YOUR_TOKEN" https://localhost:8000/api/users/me/

# Or use VS Code REST Client extension
```

## 📞 Team Communication

- **Code Review:** Every PR requires review before merge
- **Conflicts:** Signal via Discord if modifying shared code
- **Database:** Migrations coordinated before merge
- **API Changes:** Notify frontend team of endpoint changes

## ✅ Before Committing

- [ ] All tests pass: `python manage.py test`
- [ ] No console errors/warnings
- [ ] Code formatted: `black apps/`
- [ ] No hardcoded secrets
- [ ] Docstrings added to functions
- [ ] Migrations created if model changed

---

**Questions?** Check Django docs or ask the Tech Lead (@ribana-b).
