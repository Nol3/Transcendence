#!/bin/bash

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Helper functions
print_header() {
    echo -e "\n${BLUE}==================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}==================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Check prerequisites
print_header "1. Verificando requisitos"

if ! command -v docker &> /dev/null; then
    print_error "Docker no está instalado"
    exit 1
fi
print_success "Docker instalado: $(docker --version)"

if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    print_error "Docker Compose no está instalado"
    exit 1
fi
print_success "Docker Compose instalado: $($DOCKER_COMPOSE version)"

if ! command -v curl &> /dev/null; then
    print_warning "curl no instalado, se usará wget para verificaciones"
fi

# Check if .env exists
print_header "2. Verificando configuración"

if [ ! -f ".env" ]; then
    print_warning ".env no encontrado, creando con valores por defecto"
    cat > .env << 'EOF'
# Backend
BACKEND_PORT=8000
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3
CORS_ALLOWED_ORIGINS=http://localhost:4200,http://localhost:3000

# Frontend
FRONTEND_PORT=4200
NG_ENV=production
BACKEND_URL=http://localhost:8000
EOF
    print_info "Archivo .env creado con valores por defecto"
    print_warning "Revisa los valores de SECRET KEYS en .env antes de producción"
else
    print_success ".env encontrado"
fi

# Check Docker daemon
print_header "3. Verificando Docker daemon"

if ! docker ps &> /dev/null; then
    print_error "Docker daemon no está corriendo"
    exit 1
fi
print_success "Docker daemon activo"

# Stop existing containers (if any)
print_header "4. Limpiando contenedores anteriores"

if $DOCKER_COMPOSE ps | grep -q "Up"; then
    print_info "Deteniendo contenedores existentes..."
    $DOCKER_COMPOSE down --remove-orphans
    sleep 2
    print_success "Contenedores detenidos"
else
    print_info "No hay contenedores ejecutándose"
fi

# Build images
print_header "5. Compilando imágenes Docker"

print_info "Backend..."
$DOCKER_COMPOSE build backend
print_success "Backend compilado"

print_info "Frontend..."
$DOCKER_COMPOSE build frontend
print_success "Frontend compilado"

# Start services
print_header "6. Iniciando servicios"

print_info "Lanzando contenedores con $DOCKER_COMPOSE up..."
$DOCKER_COMPOSE up -d

print_info "Esperando a que servicios estén healthy..."
sleep 5

# Check service health
print_header "7. Verificando salud de servicios"

check_service_health() {
    local service=$1
    local max_attempts=30
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        health=$($DOCKER_COMPOSE ps $service | grep -o "healthy\|unhealthy\|exited" | tail -1)

        if [ "$health" = "healthy" ]; then
            print_success "$service está healthy"
            return 0
        fi

        if [ "$health" = "exited" ]; then
            print_error "$service exited"
            $DOCKER_COMPOSE logs $service | tail -20
            return 1
        fi

        attempt=$((attempt + 1))
        echo -ne "\r${YELLOW}Esperando $service... ($attempt/$max_attempts)${NC}"
        sleep 1
    done

    print_warning "$service no alcanzó healthy state, continuando..."
    return 0
}

check_service_health "backend"
check_service_health "frontend"
check_service_health "nginx"

# Create test users if backend is up
if $DOCKER_COMPOSE ps backend | grep -q "Up"; then
    print_info "Creando usuarios de prueba..."
    $DOCKER_COMPOSE exec -T backend python manage.py shell << 'EOF'
from django.contrib.auth.models import User
from apps.users.models import UserProfile

if not User.objects.filter(username='admin').exists():
    admin = User.objects.create_superuser(username='admin', email='admin@transcendence.local', password='admin123')
    UserProfile.objects.create(user=admin)
    print('Created: admin / admin123')
else:
    admin = User.objects.get(username='admin')
    admin.set_password('admin123')
    admin.save()
    print('admin password updated to admin123')

if not User.objects.filter(username='testuser').exists():
    user = User.objects.create_user(username='testuser', email='test@transcendence.local', password='test123')
    UserProfile.objects.create(user=user)
    print('Created: testuser / test123')

for i in range(1, 6):
    username = f'player{i}'
    if not User.objects.filter(username=username).exists():
        user = User.objects.create_user(username=username, email=f'{username}@test.com', password='password123')
        UserProfile.objects.create(user=user)
        print(f'Created: {username} / password123')
EOF
    print_success "Usuarios de prueba creados"
fi

echo ""

# Verify endpoints
print_header "8. Verificando endpoints"

BACKEND_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:4200"
NGINX_URL="https://localhost"

# Backend health check
print_info "Backend: $BACKEND_URL"
if curl -sf "$BACKEND_URL/admin/" &> /dev/null; then
    print_success "Backend respondiendo"
else
    print_warning "Backend aún no responde (puede estar inicializando)"
fi

# Frontend health check
print_info "Frontend: $FRONTEND_URL"
if curl -sf "$FRONTEND_URL" &> /dev/null; then
    print_success "Frontend respondiendo"
else
    print_warning "Frontend aún no responde"
fi

# Nginx health check
print_info "Nginx (HTTPS): $NGINX_URL"
if curl -k -sf "$NGINX_URL/" &> /dev/null; then
    print_success "Nginx respondiendo"
else
    print_warning "Nginx aún no responde"
fi

# Show container status
print_header "9. Estado de contenedores"

$DOCKER_COMPOSE ps

# Display useful information
print_header "10. URLs de acceso"

print_success "Frontend (desarrollo): http://localhost:4200"
print_success "Backend API: http://localhost:8000"
print_success "Backend Admin: http://localhost:8000/admin/"
print_success "Nginx (HTTPS): https://localhost"
print_success "Nginx (HTTP): http://localhost"

echo -e "\n${BLUE}Credenciales de prueba:${NC}"
echo -e "  - admin / admin123"
echo -e "  - testuser / test123"
echo -e "  - player1 / password123 (hasta player5)"

# Show logs tip
print_header "Próximos pasos"

echo -e "${BLUE}Ver logs en tiempo real:${NC}"
echo "  $DOCKER_COMPOSE logs -f backend"
echo "  $DOCKER_COMPOSE logs -f frontend"
echo "  $DOCKER_COMPOSE logs -f nginx"

echo ""
echo -e "${BLUE}Detener servicios:${NC}"
echo "  $DOCKER_COMPOSE down"

echo ""
echo -e "${BLUE}Reconstruir servicios:${NC}"
echo "  $DOCKER_COMPOSE up -d --build"

# Final status
print_header "Estado final"

# Count healthy services
healthy=$($DOCKER_COMPOSE ps | grep healthy | wc -l)
total=$($DOCKER_COMPOSE ps | grep -c "")

if [ $healthy -ge 2 ]; then
    print_success "Setup completado exitosamente"
    print_info "Todos los servicios están en funcionamiento"
else
    print_warning "Algunos servicios pueden estar inicializándose"
    print_info "Espera unos segundos y verifica de nuevo con: $DOCKER_COMPOSE ps"
fi

echo ""
