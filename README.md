# ft_transcendence

*This project has been created as part of the 42 curriculum by \<alcarden\>, \<pjimenez\>, \<ribana-b\>, \<jjaen-mo\>.*

---

## Table of Contents

1. [Description](#description)
2. [Team Information](#team-information)
3. [Project Management](#project-management)
4. [Roadmap & Milestones](#roadmap--milestones)
5. [Technical Stack](#technical-stack)
6. [Database Schema](#database-schema)
7. [Features List](#features-list)
8. [Modules](#modules)
9. [Individual Contributions](#individual-contributions)
10. [Instructions](#instructions)
11. [Resources](#resources)

---

## Description

**ft_transcendence** is the final Common Core project at 42, a full-stack web application built by a team of 4. The project consists of a **\[PROJECT NAME — to be decided by the team\]**, a real-world web app that demonstrates mastery of modern web development: frontend frameworks, backend services, real-time communication, authentication, containerised deployment and more.

### Key Features

> 🚧 *To be filled in by the team once the project concept is agreed upon.*

- Feature 1 — description
- Feature 2 — description
- Feature 3 — description
- ...

---

## Team Information

| Login | Role(s) | Responsibilities |
|-------|---------|-----------------|
| \<alcarden\> | **Product Owner (PO)** + Developer | Defines product vision, maintains backlog, validates completed work, communicates with evaluators. Also implements \[module/feature\]. |
| \<pjimenez\> | **Project Manager (PM) / Scrum Master** + Developer | Organises meetings, tracks deadlines, removes blockers, manages risks. Also implements \[module/feature\]. |
| \<ribana-b\> | **Tech Lead / Architect** + Developer | Defines technical architecture, makes stack decisions, ensures code quality and reviews critical changes. Also implements \[module/feature\]. |
| \<jjaen-mo\> | **Developer** | Implements assigned features and modules, participates in code reviews, tests and documents work. |

> **Note for evaluators:** All team members are present, understand the project as a whole, and can explain their individual contributions.

---

## Project Management

### Organisation

- **Methodology:** Agile / Scrum-lite — weekly sprint planning sessions and daily async standups.
- **Task tracking:** GitHub Issues + GitHub Projects board (Kanban columns: `Backlog → In Progress → Review → Done`).
- **Code reviews:** Every PR requires at least one review from another team member before merging to `main`.
- **Branch strategy:** `main` (protected, deployable) → `dev` (integration) → `feature/<name>` (individual work).

### Communication Channels

- **Discord** — daily async communication, progress updates, decisions log channel.
- **Weekly video call** — sprint review + planning (every Monday, ~1h).

### Work Breakdown

The project is broken down into three phases:

1. **Phase 1 — Foundation:** Mandatory infrastructure (Docker, DB, auth, frontend scaffold).
2. **Phase 2 — Modules:** Each team member owns one or more modules end-to-end.
3. **Phase 3 — Polish & Testing:** Cross-browser tests, security audit, README completion, evaluation prep.

---

## Roadmap & Milestones

> Status legend: ✅ Done · 🔄 In Progress · ⏳ Pending · ❌ Blocked

### Milestone 0 — Project Setup ⏳

| Task | Owner | Status |
|------|-------|--------|
| Agree on project concept and app name | All | ⏳ |
| Create GitHub repository and branch strategy | \<ribana-b\> | ⏳ |
| Write initial README skeleton | \<pjimenez\> | ⏳ |
| Set up `.env.example` and `.gitignore` | \<ribana-b\> | ⏳ |
| Decide on tech stack (vote + justification) | All | ⏳ |
| Choose modules (to reach ≥ 14pts) | All | ⏳ |

---

### Milestone 1 — Docker & Infrastructure ⏳

| Task | Owner | Status |
|------|-------|--------|
| `docker-compose.yml` with frontend + backend + DB services | \<ribana-b\> | ⏳ |
| Single-command startup (`docker compose up`) works | \<ribana-b\> | ⏳ |
| HTTPS configured on all backend routes | \<ribana-b\> | ⏳ |
| Environment variable management (`.env` + `.env.example`) | \<jjaen-mo\> | ⏳ |
| No sensitive credentials in repository (audit) | All | ⏳ |

---

### Milestone 2 — Database & Backend Foundation ⏳

| Task | Owner | Status |
|------|-------|--------|
| Database schema designed and documented | \<ribana-b\> | ⏳ |
| Schema implemented (migrations / ORM setup) | \<jjaen-mo\> | ⏳ |
| Backend framework scaffolded with routing | \<ribana-b\> | ⏳ |
| User sign-up endpoint (email + hashed/salted password) | \<alcarden\> | ⏳ |
| User login endpoint + session/token management | \<alcarden\> | ⏳ |
| Backend form validation (server-side) | \<alcarden\> | ⏳ |

---

### Milestone 3 — Frontend Foundation ⏳

| Task | Owner | Status |
|------|-------|--------|
| Frontend framework scaffolded | \<pjimenez\> | ⏳ |
| CSS framework / styling solution integrated | \<pjimenez\> | ⏳ |
| Responsive layout (desktop + mobile tested) | \<pjimenez\> | ⏳ |
| Sign-up / login pages with client-side validation | \<pjimenez\> | ⏳ |
| Privacy Policy page (accessible from footer) | \<jjaen-mo\> | ⏳ |
| Terms of Service page (accessible from footer) | \<jjaen-mo\> | ⏳ |
| Zero console errors/warnings in Chrome (latest stable) | All | ⏳ |
| Multi-user support tested (concurrent sessions) | All | ⏳ |

---

### Milestone 4 — Modules Implementation ⏳

> Each module row maps to the point system: **Major = 2pts · Minor = 1pt**

| Module | Category | Type | pts | Owner | Status |
|--------|----------|------|-----|-------|--------|
| \[Module 1\] | \[Category\] | Major/Minor | 2/1 | \<alcarden\> | ⏳ |
| \[Module 2\] | \[Category\] | Major/Minor | 2/1 | \<alcarden\> | ⏳ |
| \[Module 3\] | \[Category\] | Major/Minor | 2/1 | \<alcarden\> | ⏳ |
| \[Module 4\] | \[Category\] | Major/Minor | 2/1 | \<alcarden\> | ⏳ |
| \[Module 5\] | \[Category\] | Major/Minor | 2/1 | \<alcarden\> | ⏳ |
| \[Module 6\] | \[Category\] | Major/Minor | 2/1 | \<alcarden\> | ⏳ |
| **TOTAL** | | | **≥14** | | |

> **Important module dependencies to verify before claiming:**
> - Gaming modules (AI Opponent, Tournament, Customization, Spectator, Multiplayer 3+, Add another game) **require at least one game to be implemented first.**
> - Game Statistics module **requires a functional game.**
> - Advanced Chat **requires the basic chat from "User interaction" module.**
> - SSR **is incompatible with ICP blockchain backend.**

---

### Milestone 5 — Quality, Security & Testing ⏳

| Task | Owner | Status |
|------|-------|--------|
| Cross-browser test: latest Chrome (mandatory) | All | ⏳ |
| Input validation — XSS / SQL injection attempts on all forms | All | ⏳ |
| Git history shows commits from all 4 members | All | ⏳ |
| Commit messages are clear and meaningful (audit) | All | ⏳ |
| Privacy Policy content is relevant (not placeholder) | \<jjaen-mo\> | ⏳ |
| Terms of Service content is relevant (not placeholder) | \<jjaen-mo\> | ⏳ |
| `.env` is in `.gitignore` and `.env.example` is provided | \<ribana-b\> | ⏳ |
| No sensitive credentials in repository (final audit) | All | ⏳ |

---

### Milestone 6 — Evaluation Preparation ⏳

| Task | Owner | Status |
|------|-------|--------|
| README complete with ALL required sections | \<pjimenez\> | ⏳ |
| Database schema visual/description in README | \<ribana-b\> | ⏳ |
| Each team member can explain the full project | All | ⏳ |
| Each team member can explain their own contributions | All | ⏳ |
| Module demo rehearsal (every module demonstrated) | All | ⏳ |
| `git clone` + `docker compose up` works in fresh folder | All | ⏳ |
| Bonus modules documented and justified (if any) | All | ⏳ |

---

### Bonus Milestone — Extra Modules (only if ≥14pts mandatory validated) ⏳

> Maximum **5 bonus points** (e.g. 2 Major + 1 Minor, or 5 Minor).

| Module | Type | pts | Owner | Status |
|--------|------|-----|-------|--------|
| \[Bonus Module 1\] | Major/Minor | 2/1 | \<alcarden\> | ⏳ |
| \[Bonus Module 2\] | Major/Minor | 2/1 | \<alcarden\> | ⏳ |
| **BONUS TOTAL** | | **≤5** | | |

---

## Technical Stack

### Frontend

| Technology | Version | Justification |
|------------|---------|---------------|
| Angular | 18.x | Modern framework with strong typing, dependency injection, and excellent tooling for large applications. |
| Bootstrap 5 / Tailwind CSS | Latest | Responsive design and quick UI prototyping with utility-first CSS. |

### Backend

| Technology | Version | Justification |
|------------|---------|---------------|
| Django | 4.2 LTS | Robust, mature framework with built-in ORM, authentication, and admin panel. |
| Django REST Framework | 3.14.x | Industry-standard for building REST APIs with Django. |
| FastAPI (optional modules) | 0.104.x | High-performance async API for real-time features like WebSockets if needed. |

### Database

| Technology | Justification |
|------------|---------------|
| SQLite | Lightweight, zero-configuration database. Perfect for development and deployment in containers. |

### Infrastructure & DevOps

| Technology | Role |
|------------|------|
| Docker & Docker Compose | Containerised deployment — all services (frontend, backend, DB) run in containers with single-command startup. |
| Nginx | Reverse proxy for frontend and load balancing. |
| HTTPS (self-signed in dev) | Secure backend connections. |

### Development Tools

| Tool | Purpose |
|------|---------|
| Git / GitHub | Version control with branch strategy for team collaboration. |
| Environment variables (.env) | Configuration management for different environments. |

---

## Database Schema

> 🚧 *To be added once the schema is finalised. Include an ERD diagram (image or ASCII) and a description of each table/collection with key fields and relationships.*

```
Example structure:

users
  id          UUID PK
  email       VARCHAR UNIQUE NOT NULL
  password    VARCHAR NOT NULL (hashed + salted)
  username    VARCHAR UNIQUE NOT NULL
  avatar_url  VARCHAR
  created_at  TIMESTAMP

[table 2]
  ...
```

---

## Features List

> 🚧 *To be filled as features are implemented.*

| Feature | Description | Implemented by |
|---------|-------------|----------------|
| User Registration | Email + password signup with hashed passwords | |
| User Login | Secure login with session/JWT management | |
| \[Feature N\] | \[Description\] | |

---

## Modules

> Total claimed: **X Major (Xpts) + X Minor (Xpts) = X pts** (must be ≥ 14 to pass)

### Major Modules (2 pts each)

#### \[Module Name\] — Web / User Management / AI / Gaming / Devops / …

- **Description:** What it does and how it was implemented.
- **Implemented by:** \<alcarden\>
- **Justification:** Why this module was chosen and how it adds value.
- **Dependencies met:** \[e.g. "Game module implemented first" / "N/A"\]

---

### Minor Modules (1 pt each)

#### \[Module Name\]

- **Description:** What it does and how it was implemented.
- **Implemented by:** \<alcarden\>
- **Justification:** Why this module was chosen.
- **Dependencies met:** \[e.g. "N/A"\]

---

### Custom "Modules of Choice" (if any)

For each custom module, include:

- **Why we chose this module:** …
- **Technical challenges it addresses:** …
- **How it adds value to the project:** …
- **Why it deserves Major/Minor status:** …
- **Implemented by:** \<alcarden\>

---

## Individual Contributions

### \<alcarden\> — Product Owner + Developer

- Managed product backlog and feature priorities.
- \[Feature / module implemented\] — description of technical work done.
- Challenges faced: …
- How they were overcome: …

### \<pjimenez\> — Project Manager + Developer

- Organised sprint planning and tracked deadlines.
- \[Feature / module implemented\] — description of technical work done.
- Challenges faced: …
- How they were overcome: …

### \<ribana-b\> — Tech Lead + Developer

- Designed system architecture and made key stack decisions.
- \[Feature / module implemented\] — description of technical work done.
- Challenges faced: …
- How they were overcome: …

### \<jjaen-mo\> — Developer

- \[Feature / module implemented\] — description of technical work done.
- Challenges faced: …
- How they were overcome: …

---

## Instructions

### Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Docker | ≥ 24.x | Install from [docker.com](https://www.docker.com) |
| Docker Compose | ≥ 2.x | Included with Docker Desktop |
| Git | any recent | For version control |

> **No other software needs to be installed locally** — all frontend and backend dependencies run inside containers with `docker compose up`.

### Quick Start (Docker)

```bash
# 1. Clone the repository
git clone <repo-url> ft_transcendence
cd ft_transcendence

# 2. Set up environment
cp .env.example .env
chmod +x docker/generate-ssl.sh
docker/generate-ssl.sh

# 3. Start all services
docker compose up --build

# 4. Open the application
# Frontend: https://localhost:4200
# Backend API: https://localhost:8000
# Django Admin: https://localhost:8000/admin
```

### Environment Variables

See `.env.example` for all available variables. Essential ones:

| Variable | Description | Example |
|----------|-------------|---------|
| `DJANGO_SECRET_KEY` | Django secret key | `your-super-secret-key` |
| `JWT_SECRET_KEY` | JWT signing key | `your-jwt-secret` |
| `DJANGO_DEBUG` | Debug mode | `false` (production), `true` (dev) |
| `CORS_ALLOWED_ORIGINS` | Allowed frontend origins | `http://localhost:4200` |

### Stopping the Application

```bash
# Stop all services
docker compose down

# Stop and remove all data (wipes database)
docker compose down -v

# Stop specific service
docker compose stop backend
```

### Detailed Documentation

- **[DEVELOPMENT.md](docs/DEVELOPMENT.md)** — Complete development guide with project structure, team workflow, API endpoints, troubleshooting
- **[Backend README](backend/README.md)** — Django app structure and how to extend
- **[Frontend README](frontend/README.md)** — Angular module structure and component guidelines

---

## Resources

### Documentation

- [Docker Documentation](https://docs.docker.com/)
- [OWASP — Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- [MDN Web Docs](https://developer.mozilla.org/)
- \[Frontend framework official docs — link\]
- \[Backend framework official docs — link\]
- \[Database official docs — link\]

### Articles & Tutorials

> 🚧 *To be filled as the team researches the project.*

- …

### How AI Was Used

> As per the 42 AI Guidelines, we used AI tools responsibly — only for content we fully understood and could explain.

| Task / Area | AI Tool Used | How it was used |
|-------------|-------------|-----------------|
| Boilerplate generation | \[e.g. GitHub Copilot\] | Generated initial scaffold; reviewed and modified by the team. |
| Debugging | \[e.g. Claude\] | Used to understand error messages; solutions were understood before applying. |
| Documentation | \[e.g. Claude\] | Helped draft sections; all content reviewed and validated by the team. |
| \[Other task\] | | |

> All AI-generated code was reviewed with peers before inclusion. No AI output was blindly copy-pasted.

---

*Last updated: \[date\] by \[login\]*
