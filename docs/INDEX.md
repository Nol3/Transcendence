# 📚 FT Transcendence - Documentation Index

Welcome to FT Transcendence! This is your complete documentation guide for the project.

## 🚀 Getting Started

**New to the project?** Start here:

1. **[README.md](README.md)** — Project overview, team info, tech stack
2. **[QUICKREF.md](QUICKREF.md)** — Common commands and quick reference
3. **[setup.sh](setup.sh)** — Automated setup script

## 📋 Main Documentation

### For Everyone
- **[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)** — Complete development guide
  - Project structure
  - Architecture overview
  - Development workflow
  - API endpoints
  - Troubleshooting
  
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — How to contribute
  - Git workflow & branching
  - Code style guidelines
  - Code review process
  - Team communication

### Backend Developers
- **[backend/README.md](backend/README.md)** — Django API documentation
  - Django apps structure (users, games, chat, tournament)
  - Model definitions
  - API endpoints reference
  - Adding new endpoints
  - Testing

### Frontend Developers  
- **[frontend/README.md](frontend/README.md)** — Angular app documentation
  - Project structure
  - Component development
  - Services & models
  - Routing
  - Styling guidelines
  - Testing

### DevOps / Infrastructure
- **[docker-compose.yml](docker-compose.yml)** — Service orchestration
- **[docker/](docker/)** — Container configs
  - Dockerfile.backend
  - Dockerfile.frontend
  - nginx configuration
  - SSL setup

### Local Development
- **[docs/LOCAL_DEVELOPMENT.md](docs/LOCAL_DEVELOPMENT.md)** — Setup without Docker
  - Python/Django local setup
  - Node/Angular local setup
  - API testing
  - Debugging tips

## 📂 Project Structure

```
ft_transcendence/
├── 📖 README.md                    # Main project README
├── 📖 CONTRIBUTING.md              # Contribution guidelines
├── 📖 QUICKREF.md                  # Quick command reference
├── 🐳 docker-compose.yml           # Docker orchestration
├── .env.example                   # Environment variables template
│
├── frontend/                       # Angular 18 application
│   ├── src/
│   │   ├── app/                   # Application logic
│   │   │   ├── modules/           # Feature modules (auth, games, chat, etc.)
│   │   │   ├── shared/            # Reusable components
│   │   │   ├── services/          # API services
│   │   │   └── models/            # Interfaces & types
│   │   └── assets/                # Static assets
│   ├── angular.json               # Angular config
│   ├── package.json               # Dependencies
│   └── 📖 README.md               # Frontend documentation
│
├── backend/                        # Django REST API application
│   ├── config/                    # Project configuration
│   │   ├── settings.py            # Django settings
│   │   ├── urls.py                # URL routes
│   │   ├── asgi.py                # WebSocket config
│   │   └── wsgi.py                # Production config
│   ├── apps/                      # Django applications
│   │   ├── users/                 # User authentication
│   │   ├── games/                 # Game logic
│   │   ├── chat/                  # Messaging
│   │   └── tournament/            # Tournament management
│   ├── manage.py                  # Django CLI
│   ├── requirements.txt           # Python dependencies
│   └── 📖 README.md               # Backend documentation
│
├── docker/                         # Docker configuration
│   ├── Dockerfile.backend         # Backend container
│   ├── Dockerfile.frontend        # Frontend container
│   ├── nginx.conf                 # Reverse proxy config
│   ├── nginx-app.conf            # App server config
│   ├── generate-ssl.sh           # SSL certificate generation
│   └── ssl/                       # SSL certificates
│
├── docs/                           # Documentation
│   ├── 📖 DEVELOPMENT.md          # Complete dev guide
│   └── 📖 LOCAL_DEVELOPMENT.md    # Local setup without Docker
│
└── setup.sh                        # Automated setup script
```

## 🎯 Quick Navigation by Role

### 👨‍💼 Project Manager / Product Owner
- [README.md](README.md) — Project vision & status
- [CONTRIBUTING.md](CONTRIBUTING.md) — Team workflow
- [QUICKREF.md](QUICKREF.md) — Commands for demos

### 👨‍💻 Backend Developer
- [backend/README.md](backend/README.md) — API docs
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) — Architecture
- [docs/LOCAL_DEVELOPMENT.md](docs/LOCAL_DEVELOPMENT.md) — Local setup

### 🎨 Frontend Developer
- [frontend/README.md](frontend/README.md) — Component guide
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) — Project scope
- [CONTRIBUTING.md](CONTRIBUTING.md) — Code standards

### 🚀 DevOps / Full Stack
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) — Full architecture
- Docker files in [docker/](docker/)
- [docker-compose.yml](docker-compose.yml) — Service config

## 🎓 Learning Path

### First Time Setup
1. Read [README.md](README.md)
2. Run [setup.sh](setup.sh)
3. Check [QUICKREF.md](QUICKREF.md)

### Understanding the Architecture
1. Read [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)
2. Review [docker-compose.yml](docker-compose.yml)
3. Check service-specific README files

### Starting Development
1. Review [CONTRIBUTING.md](CONTRIBUTING.md)
2. Choose backend or frontend path:
   - **Backend:** [backend/README.md](backend/README.md) → [docs/LOCAL_DEVELOPMENT.md](docs/LOCAL_DEVELOPMENT.md)
   - **Frontend:** [frontend/README.md](frontend/README.md) → [docs/LOCAL_DEVELOPMENT.md](docs/LOCAL_DEVELOPMENT.md)

### Making Your First PR
1. Create feature branch (see [CONTRIBUTING.md](CONTRIBUTING.md))
2. Reference appropriate docs for your module
3. Follow code style in [CONTRIBUTING.md](CONTRIBUTING.md)
4. Ensure tests pass
5. Request review

## 🔧 Common Tasks

### I want to...

**Set up the project locally**
→ Run `./setup.sh` or follow [docs/LOCAL_DEVELOPMENT.md](docs/LOCAL_DEVELOPMENT.md)

**Understand the architecture**
→ Read [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md#🏗️-architecture)

**Start working on the backend**
→ [backend/README.md](backend/README.md)

**Start working on the frontend**
→ [frontend/README.md](frontend/README.md)

**Learn about API endpoints**
→ [backend/README.md](backend/README.md#📚-apps-overview)

**Add a new component**
→ [frontend/README.md](frontend/README.md#🏗️-creating-a-new-component)

**Add a new API endpoint**
→ [backend/README.md](backend/README.md#📝-adding-new-endpoints)

**Deploy to Docker**
→ `-compose.yml` + [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md#setup-instructions)

**Debug an issue**
→ [QUICKREF.md](QUICKREF.md#🚨-troubleshooting)

**Contribute code**
→ [CONTRIBUTING.md](CONTRIBUTING.md)

## 📞 Getting Help

1. **Check documentation first** — Most answers are here
2. **Search project issues** — Your question might be answered
3. **Ask in Discord** — Team is available to help
4. **Schedule sync meeting** — For complex issues

## 📊 Status Overview

| Component | Status | Owner |
|-----------|--------|-------|
| Project Setup | ✅ Complete | Team |
| Docker Infrastructure | ✅ Complete | ribana-b |
| Django Backend | 🔄 In Progress | alcarden, ribana-b |
| Angular Frontend | 🔄 In Progress | pjimenez, jjaen-mo |
| Database (SQLite) | ✅ Ready | Team |
| Documentation | ✅ Complete | Team |

## 🚀 Next Steps

1. ✅ Clone repository
2. ✅ Run `./setup.sh`
3. ✅ Access frontend at https://localhost:4200
4. ✅ Start developing!

## 📚 External Resources

- [Angular Documentation](https://angular.io/docs)
- [Django Documentation](https://docs.djangoproject.com/)
- [Docker Documentation](https://docs.docker.com/)
- [Bootstrap 5](https://getbootstrap.com/)
- [REST API Best Practices](https://restfulapi.net/)

---

**Last Updated:** March 23, 2026
**Documentation Version:** 1.0
**Questions?** Check the relevant README or ask in Discord! 🎉
