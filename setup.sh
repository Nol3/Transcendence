#!/bin/bash
# Quick start script for ft_transcendence
# This script automates the initial setup

set -e  # Exit on error

echo "🚀 ft_transcendence - Quick Start Setup"
echo "========================================"
echo ""

# Check prerequisites
echo "✅ Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"
echo ""

# Setup environment file
echo "📝 Setting up environment variables..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Created .env file from .env.example"
    echo "⚠️  Please review .env and update values if needed"
else
    echo "✅ .env file already exists, skipping"
fi
echo ""

# Generate SSL certificates
echo "🔐 Generating SSL certificates..."
if [ ! -f docker/ssl/cert.pem ] || [ ! -f docker/ssl/ssl/key.pem ]; then
    chmod +x docker/generate-ssl.sh
    docker/generate-ssl.sh
    echo "✅ SSL certificates generated"
else
    echo "✅ SSL certificates already exist"
fi
echo ""

# Build and start services
echo "🐳 Building and starting Docker services..."
echo "This may take a few minutes on first run..."
echo ""

docker compose up --build -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check services health
echo "🏥 Checking service health..."

# Check backend
if docker compose exec -T backend curl -f http://localhost:8000/api/health/ > /dev/null 2>&1; then
    echo "✅ Backend is ready"
else
    echo "⚠️  Backend is still starting..."
fi

# Run migrations
echo "🔄 Running database migrations..."
docker compose exec -T backend python manage.py migrate

# Create superuser with default credentials (development only)
echo "👤 Creating/updating superuser account..."
docker compose exec -T backend python manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin')
    print("✅ Superuser created (username: admin, password: admin)")
else:
    print("✅ Superuser already exists")
END

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📍 Access the application:"
echo "   Frontend:  https://localhost:4200"
echo "   Backend:   https://localhost:8000"
echo "   Admin:     https://localhost:8000/admin (admin/admin)"
echo ""
echo "💡 Useful commands:"
echo "   docker compose logs -f backend      # View backend logs"
echo "   docker compose logs -f frontend     # View frontend logs"
echo "   docker compose down                 # Stop all services"
echo "   docker compose down -v              # Stop and remove volumes (wipes DB)"
echo ""
echo "📚 Documentation:"
echo "   docs/DEVELOPMENT.md     - Complete development guide"
echo "   backend/README.md       - Backend documentation"
echo "   frontend/README.md      - Frontend documentation"
echo ""
echo "✨ Happy coding! 🚀"
