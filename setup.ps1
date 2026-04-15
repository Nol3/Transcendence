# =============================================================================
# ft_transcendence - Setup Script for Local Development
# =============================================================================
# This script sets up the entire project from scratch.
# Run this script from the project root directory.
#
# Usage:
#   .\setup.ps1           - Full setup (creates venv, installs deps, runs migrations)
#   .\setup.ps1 -SkipDeps - Skip dependency installation (already installed)
#   .\setup.ps1 -Dev      - Start in development mode with both servers
# =============================================================================

param(
    [switch]$SkipDeps,
    [switch]$Dev
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot

function Write-Step {
    param([string]$Message)
    Write-Host "`n[SETUP] $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# =============================================================================
# CHECK REQUIREMENTS
# =============================================================================

Write-Step "Checking requirements..."

# Check Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not installed. Please install Python 3.10+ from https://www.python.org/downloads/"
    exit 1
}
$pythonVersion = python --version 2>&1
Write-Success "Python: $pythonVersion"

# Check Node.js
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Error "Node.js is not installed. Please install Node.js 18+ from https://nodejs.org/"
    exit 1
}
$nodeVersion = node --version 2>&1
Write-Success "Node.js: $nodeVersion"

# Check npm
$npmVersion = npm --version 2>&1
Write-Success "npm: $npmVersion"

# =============================================================================
# BACKEND SETUP
# =============================================================================

Write-Step "Setting up Backend..."

$BackendDir = Join-Path $ProjectRoot "backend"
$VenvDir = Join-Path $BackendDir "venv"

# Create virtual environment
Write-Step "Creating Python virtual environment..."
if (Test-Path $VenvDir) {
    Write-Warning "Virtual environment already exists. Skipping creation."
} else {
    python -m venv $VenvDir
    Write-Success "Virtual environment created at: $VenvDir"
}

# Activate virtual environment and install dependencies
Write-Step "Installing Python dependencies..."
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$VenvPip = Join-Path $VenvDir "Scripts\pip.exe"

if (-not $SkipDeps) {
    & $VenvPip install --upgrade pip
    & $VenvPip install -r (Join-Path $BackendDir "requirements.txt")
    Write-Success "Python dependencies installed"
} else {
    Write-Warning "Skipping dependency installation"
}

# Run migrations
Write-Step "Running database migrations..."
Set-Location $BackendDir
& $VenvPython manage.py migrate --noinput
Write-Success "Database migrations completed"

# Create test users
Write-Step "Creating test users..."
& $VenvPython manage.py shell -c @"
from django.contrib.auth.models import User
from apps.users.models import UserProfile

# Create admin user
if not User.objects.filter(username='admin').exists():
    admin = User.objects.create_superuser(username='admin', email='admin@transcendence.local', password='admin123')
    UserProfile.objects.create(user=admin)
    print('Created: admin / admin123')
else:
    print('admin already exists')

# Create test user
if not User.objects.filter(username='testuser').exists():
    user = User.objects.create_user(username='testuser', email='test@transcendence.local', password='test123')
    UserProfile.objects.create(user=user)
    print('Created: testuser / test123')
else:
    print('testuser already exists')

# Create player users
for i in range(1, 6):
    username = f'player{i}'
    if not User.objects.filter(username=username).exists():
        user = User.objects.create_user(username=username, email=f'{username}@test.com', password='password123')
        UserProfile.objects.create(user=user)
        print(f'Created: {username} / password123')
"@

Write-Success "Test users created"

# =============================================================================
# FRONTEND SETUP
# =============================================================================

Write-Step "Setting up Frontend..."

$FrontendDir = Join-Path $ProjectRoot "frontend"
Set-Location $FrontendDir

if (-not $SkipDeps) {
    Write-Step "Installing npm dependencies..."
    npm install
    Write-Success "npm dependencies installed"
} else {
    Write-Warning "Skipping npm installation"
}

# =============================================================================
# COMPLETION
# =============================================================================

Write-Host "`n" -NoNewline
Write-Host "========================================" -ForegroundColor Green
Write-Host "  SETUP COMPLETED SUCCESSFULLY!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "`n"

# Check if user wants to start the servers
if ($Dev) {
    Write-Step "Starting development servers..."

    Write-Host "`n[BACKEND] Starting Django server on http://localhost:8000" -ForegroundColor Yellow
    Start-Process -FilePath $VenvPython -ArgumentList "manage.py runserver 8000" -WorkingDirectory $BackendDir -NoNewWindow

    Write-Host "[FRONTEND] Starting Angular server on http://localhost:4200" -ForegroundColor Yellow
    Start-Process -FilePath "npm" -ArgumentList "start" -WorkingDirectory $FrontendDir -NoNewWindow

    Start-Sleep -Seconds 3

    Write-Host "`nServers are starting..." -ForegroundColor Cyan
    Write-Host "  - Backend API:  http://localhost:8000" -ForegroundColor White
    Write-Host "  - Frontend:     http://localhost:4200" -ForegroundColor White
    Write-Host "  - Admin Panel:  http://localhost:8000/admin" -ForegroundColor White
    Write-Host "`nTest credentials:" -ForegroundColor Cyan
    Write-Host "  - admin / admin123" -ForegroundColor White
    Write-Host "  - testuser / test123" -ForegroundColor White
    Write-Host "`nPress Ctrl+C to stop the servers.`n" -ForegroundColor Yellow

    # Wait for user interrupt
    try {
        while ($true) { Start-Sleep -Seconds 1 }
    } catch {
        Write-Host "`nStopping servers..." -ForegroundColor Yellow
        Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*runserver*" } | Stop-Process -Force
        Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*ng serve*" } | Stop-Process -Force
    }
} else {
    Write-Host "To start the servers, run:" -ForegroundColor Cyan
    Write-Host "`n  # Terminal 1 - Backend" -ForegroundColor White
    Write-Host "  cd backend" -ForegroundColor Gray
    Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor Gray
    Write-Host "  python manage.py runserver 8000" -ForegroundColor Gray
    Write-Host "`n  # Terminal 2 - Frontend" -ForegroundColor White
    Write-Host "  cd frontend" -ForegroundColor Gray
    Write-Host "  npm start" -ForegroundColor Gray
    Write-Host "`nOr simply run: .\setup.ps1 -Dev" -ForegroundColor Yellow
    Write-Host "`nTest credentials:" -ForegroundColor Cyan
    Write-Host "  - admin / admin123" -ForegroundColor White
    Write-Host "  - testuser / test123" -ForegroundColor White
}

Set-Location $ProjectRoot
