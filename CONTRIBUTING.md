# Contributing to FT Transcendence

Thank you for contributing to the FT Transcendence project! This guide explains how to work collaboratively as a team.

## 🎯 Team Assignments

| Member | Role | Focus Area |
|--------|------|-----------|
| **alcarden** | Product Owner | Backend: Chat module, API design |
| **pjimenez** | Project Manager | Frontend: UI/UX, components |
| **ribana-b** | Tech Lead | Backend: Games, architecture |
| **jjaen-mo** | Developer | Backend: Tournament, Frontend support |

## 📋 Development Workflow

### 1. Create a Feature Branch

Always work on a feature branch, never push directly to `dev` or `main`:

```bash
# Update local repository
git pull origin dev

# Create feature branch with descriptive name
git checkout -b feature/user-authentication
# or for bug fixes:
git checkout -b bugfix/login-issue
# or for documentation:
git checkout -b docs/api-endpoints
```

### 2. Work on Your Feature

Make incremental commits with clear, descriptive messages:

```bash
# Commit with clear message
git commit -m "feat: implement user registration endpoint"

# Good commit messages follow this pattern:
# feat: add new feature
# fix: fix a bug
# docs: update documentation
# refactor: code refactoring
# test: add/update tests
# chore: build, dependency updates
```

### 3. Push to Your Branch

```bash
git push origin feature/user-authentication
```

### 4. Create a Pull Request (PR)

**In GitHub (or your Git hosting):**
1. Open a Pull Request from your feature branch to `dev`
2. Add a descriptive title and description:
   ```
   Title: Add user registration endpoint
   
   Description:
   - Implements POST /api/users/register/
   - Validates email and password
   - Creates UserProfile automatically
   - Includes error handling for duplicate emails
   
   Related issue: #123 (if applicable)
   ```
3. Ensure CI passes (tests, linters, etc.)
4. Request review from at least one team member

### 5. Code Review

- Every PR requires at least **1 approval** before merging
- Address feedback constructively
- Update your branch if requested

```bash
# Make changes based on feedback
git add .
git commit -m "refactor: address code review feedback"
git push origin feature/user-authentication
```

### 6. Merge to Dev

Once approved:
1. Merge PR to `dev` branch via GitHub
2. Delete your feature branch (optional but recommended)
3. Pull latest changes locally:
   ```bash
   git checkout dev
   git pull origin dev
   ```

### 7. Merge Dev to Main (Release)

Only the Tech Lead (@ribana-b) merges `dev` → `main` after:
- ✅ All tests pass
- ✅ No outstanding issues
- ✅ Team review complete

```bash
git checkout main
git pull origin main
git merge dev
git push origin main
git tag v1.0.0  # Add version tag
git push origin v1.0.0
```

## 🏗️ Project Structure Guidelines

### Backend
- Each app should be **independent** — minimal cross-app dependencies
- Models in `models.py`, views in `views.py`, etc.
- Always use **serializers** for API responses
- Include **docstrings** for functions

### Frontend
- Create **feature modules** in `modules/` folder
- Keep components **small and reusable**
- Use **services** for API calls
- Follow Angular **style guide**

## 📝 Code Style

### Python (Backend)

```python
# Use type hints
def create_user(username: str, email: str) -> User:
    """Create a new user and profile.
    
    Args:
        username: User's username
        email: User's email address
        
    Returns:
        Created User object
    """
    user = User.objects.create_user(username=username, email=email)
    return user

# Follow PEP 8
# - 4 spaces for indentation
# - Max 79 characters per line
# - Imports at top, organized
```

### TypeScript (Frontend)

```typescript
// Use strict types
export interface User {
  id: number;
  username: string;
  email: string;
}

// Add JSDoc comments
/**
 * Fetches user data from backend
 * @param userId - The ID of the user to fetch
 * @returns Observable of User object
 */
getUserById(userId: number): Observable<User> {
  return this.http.get<User>(`/api/users/${userId}/`);
}

// Use const instead of var
const userName = 'John';

// Use meaningful variable names
// ❌ Bad: const u = ...
// ✅ Good: const userName = ...
```

## 🧪 Testing Requirements

### Backend
```bash
cd backend
python manage.py test
```

### Frontend
```bash
cd frontend
npm test
```

**Policy:** Submit PR only if:
- ✅ Tests pass
- ✅ Code coverage doesn't decrease
- ✅ No console errors/warnings

## 🔒 Git Security Guidelines

**Never commit:**
- 🚫 `.env` files with real credentials
- 🚫 Database files (`db.sqlite3`)
- 🚫 `node_modules/`, `.venv/`, virtual environments
- 🚫 API keys, passwords, secrets

**Before pushing, verify:**

```bash
# Check what you're committing
git status

# View changes before committing
git diff

# Ensure .env and other sensitive files are in .gitignore
cat .gitignore | grep -E '\.env|node_modules|\.venv'
```

## 🤝 Communication

### When to Communicate

**Async (Discord):**
- Daily status updates
- Questions about requirements
- Blocking issues

**Sync (Weekly Meeting):**
- Sprint planning
- Major architecture decisions
- Technical blockers
- Code review discussions

### If You're Blocked

1. **Try to unblock yourself** (check docs, search similar code)
2. **Ask in Discord** (describe what you've tried)
3. **Schedule a call** if it's complex

## 📊 Code Review Checklist

When reviewing someone's PR, check:

- ✅ Code follows team style guidelines
- ✅ Functions have docstrings
- ✅ Tests are included and pass
- ✅ No console errors/warnings
- ✅ No hardcoded secrets/credentials
- ✅ API changes documented
- ✅ Database schema changes migrated
- ✅ Performance considerations

## 🚀 Deployment Checklist

Before merging to `main`:

- ✅ Feature complete and tested
- ✅ Documentation updated
- ✅ Database migrations applied
- ✅ Environment variables documented
- ✅ Security review passed
- ✅ Performance acceptable
- ✅ No breaking changes (or documented)

## 🐛 Reporting Bugs

Create a GitHub Issue with:
1. **Title:** Brief description of bug
2. **Environment:** Docker containers, OS, browser
3. **Steps to reproduce:** Exact steps
4. **Expected behavior:** What should happen
5. **Actual behavior:** What happens instead
6. **Screenshots/logs:** If applicable

Example:
```
Title: Login fails with special characters in password

Environment: Docker, macOS, Chrome 120

Steps:
1. Go to register page
2. Enter password with @#$ characters
3. Click register

Expected: User registers successfully
Actual: Error "Invalid character in password"
```

## 📚 Documentation

When you add a feature, update:

1. **Code comments** - Explain complex logic
2. **Function docstrings** - Parameter and return types
3. **README files** - High-level overview
4. **API docs** - New endpoints in backend README
5. **Comments in this file** - If workflow changes

## 🎓 Learning Resources

- **Git:** https://git-scm.com/doc
- **Django:** https://docs.djangoproject.com/
- **Angular:** https://angular.io/docs
- **Docker:** https://docs.docker.com/
- **REST API Design:** https://restfulapi.net/

## ❓ Questions?

1. Check project documentation
2. Search GitHub issues
3. Ask in Discord
4. Contact Tech Lead (@ribana-b)

---

**Thanks for contributing! Let's build something great together! 🚀**
