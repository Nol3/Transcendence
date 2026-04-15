#!/bin/bash
# =============================================================================
# ft_transcendence - Setup Script for Local Development
# =============================================================================
# This script sets up the entire project from scratch.
# Run this script from the project root directory.
#
# Usage:
#   ./setup.sh           - Full setup (creates venv, installs deps, runs migrations)
#   ./setup.sh --skip-deps - Skip dependency installation (already installed)
#   ./setup.sh --dev     - Start in development mode with both servers
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

SKIP_DEPS=false
DEV_MODE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-deps)
            SKIP_DEPS=true
            shift
            ;;
        --dev)
            DEV_MODE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: ./setup.sh [--skip-deps] [--dev]"
            exit 1
            ;;
    esac
done

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo_step() {
    echo -e "\n${CYAN}[SETUP]${NC} $1"
}

echo_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# =============================================================================
# CHECK REQUIREMENTS
# =============================================================================

echo_step "Checking requirements..."

# Check Python
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo_error "Python is not installed. Please install Python 3.10+"
        exit 1
    fi
    PYTHON_CMD="python"
else
    PYTHON_CMD="python3"
fi
echo_success "Python: $(${PYTHON_CMD} --version)"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo_error "Node.js is not installed. Please install Node.js 18+"
    exit 1
fi
echo_success "Node.js: $(node --version)"

# Check npm
echo_success "npm: $(npm --version)"

# =============================================================================
# BACKEND SETUP
# =============================================================================

echo_step "Setting up Backend..."

BACKEND_DIR="$PROJECT_ROOT/backend"
VENV_DIR="$BACKEND_DIR/venv"

# Create virtual environment
echo_step "Creating Python virtual environment..."
if [ -d "$VENV_DIR" ]; then
    echo_warn "Virtual environment already exists. Skipping creation."
else
    $PYTHON_CMD -m venv "$VENV_DIR"
    echo_success "Virtual environment created at: $VENV_DIR"
fi

# Use venv's python and pip directly
VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"

# Install dependencies
echo_step "Installing Python dependencies..."
if [ "$SKIP_DEPS" = false ]; then
    # Use --break-system-packages for WSL/Linux systems that block global pip
    PIP_FLAGS="--break-system-packages"
    $VENV_PIP install --upgrade pip $PIP_FLAGS
    $VENV_PIP install -r "$BACKEND_DIR/requirements.txt" $PIP_FLAGS
    echo_success "Python dependencies installed"
else
    echo_warn "Skipping dependency installation"
fi

# Install dependencies
echo_step "Installing Python dependencies..."
if [ "$SKIP_DEPS" = false ]; then
    # Use --break-system-packages for WSL/Linux systems that block global pip
    PIP_FLAGS="--break-system-packages"
    pip install --upgrade pip $PIP_FLAGS
    pip install -r "$BACKEND_DIR/requirements.txt" $PIP_FLAGS
    echo_success "Python dependencies installed"
else
    echo_warn "Skipping dependency installation"
fi

# Run migrations
echo_step "Running database migrations..."
cd "$BACKEND_DIR"
$PYTHON_CMD manage.py migrate --noinput
echo_success "Database migrations completed"

# Create test users
echo_step "Creating test users..."
$PYTHON_CMD manage.py shell << 'EOF'
from django.contrib.auth.models import User
from apps.users.models import UserProfile

if not User.objects.filter(username='admin').exists():
    admin = User.objects.create_superuser(username='admin', email='admin@transcendence.local', password='admin123')
    UserProfile.objects.create(user=admin)
    print('Created: admin / admin123')
else:
    print('admin already exists')

if not User.objects.filter(username='testuser').exists():
    user = User.objects.create_user(username='testuser', email='test@transcendence.local', password='test123')
    UserProfile.objects.create(user=user)
    print('Created: testuser / test123')
else:
    print('testuser already exists')

for i in range(1, 6):
    username = f'player{i}'
    if not User.objects.filter(username=username).exists():
        user = User.objects.create_user(username=username, email=f'{username}@test.com', password='password123')
        UserProfile.objects.create(user=user)
        print(f'Created: {username} / password123')
EOF

echo_success "Test users created"

# =============================================================================
# FRONTEND SETUP
# =============================================================================

echo_step "Setting up Frontend..."

FRONTEND_DIR="$PROJECT_ROOT/frontend"
cd "$FRONTEND_DIR"

if [ "$SKIP_DEPS" = false ]; then
    echo_step "Installing npm dependencies..."
    npm install
    echo_success "npm dependencies installed"
else
    echo_warn "Skipping npm installation"
fi

# =============================================================================
# COMPLETION
# =============================================================================

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  SETUP COMPLETED SUCCESSFULLY!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

if [ "$DEV_MODE" = true ]; then
    echo_step "Starting development servers..."

    echo -e "${YELLOW}[BACKEND] Starting Django server on http://localhost:8000${NC}"
    cd "$BACKEND_DIR"
    $PYTHON_CMD manage.py runserver 8000 &
    BACKEND_PID=$!

    echo -e "${YELLOW}[FRONTEND] Starting Angular server on http://localhost:4200${NC}"
    cd "$FRONTEND_DIR"
    npm start &
    FRONTEND_PID=$!

    sleep 3

    echo ""
    echo -e "${CYAN}Servers are starting...${NC}"
    echo -e "  - Backend API:  http://localhost:8000"
    echo -e "  - Frontend:     http://localhost:4200"
    echo -e "  - Admin Panel:  http://localhost:8000/admin"
    echo ""
    echo -e "${CYAN}Test credentials:${NC}"
    echo -e "  - admin / admin123"
    echo -e "  - testuser / test123"
    echo ""
    echo -e "${YELLOW}Press Ctrl+C to stop the servers.${NC}"
    echo ""

    trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Servers stopped.'; exit" SIGINT SIGTERM
    wait
else
    echo -e "${CYAN}To start the servers, run:${NC}"
    echo ""
    echo -e "  # Terminal 1 - Backend"
    echo -e "  cd backend"
    echo -e "  source venv/bin/activate  # or venv\\Scripts\\activate on Windows"
    echo -e "  python manage.py runserver 8000"
    echo ""
    echo -e "  # Terminal 2 - Frontend"
    echo -e "  cd frontend"
    echo -e "  npm start"
    echo ""
    echo -e "Or simply run: ./setup.sh --dev"
    echo ""
    echo -e "${CYAN}Test credentials:${NC}"
    echo -e "  - admin / admin123"
    echo -e "  - testuser / test123"
fi

cd "$PROJECT_ROOT"
