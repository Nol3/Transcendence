#!/bin/bash

# Script de diagnóstico para problemas de puertos en Rootless Docker
# Uso: ./diagnose-docker.sh

echo "=================================="
echo "Diagnóstico de Rootless Docker"
echo "=================================="
echo ""

# Verificar si Docker está instalado
if ! command -v docker &> /dev/null; then
    echo "❌ Docker no está instalado"
    exit 1
fi

echo "✓ Docker instalado"
echo ""

# Verificar si es Rootless Docker
echo "Verificando modo de Docker..."
DOCKER_INFO=$(docker info 2>/dev/null)

if echo "$DOCKER_INFO" | grep -q "rootless"; then
    echo "⚠️  ROOTLESS DOCKER DETECTADO"
    echo ""
    echo "   Esto significa que Docker corre sin privilegios de administrador."
    echo "   NO puedes usar puertos < 1024 (80, 443, etc.)"
    echo ""
    echo "   SOLUCIONES:"
    echo ""
    echo "   1. Cambiar puertos en compose.yaml:"
    echo "      443:443  →  8443:443"
    echo "      80:80    →  8080:80"
    echo ""
    echo "   2. O ejecutar el script mejorado:"
    echo "      ./setup-docker.sh (versión nueva)"
    echo ""
else
    echo "✓ Docker normal (con permisos estándar)"
    echo ""
    echo "  Deberías poder usar puertos 80 y 443"
    echo "  Si ves el error, intenta:"
    echo "  - Verificar que el puerto no esté en uso: netstat -tlnp | grep :443"
    echo "  - Usar sudo: sudo docker-compose up -d"
fi

echo ""
echo "=================================="
echo "Información del sistema"
echo "=================================="
echo ""

# Información de puertos
echo "Puertos actualmente en uso:"
if command -v ss &> /dev/null; then
    ss -tlnp 2>/dev/null | grep -E ":(80|443|8080|8443)" || echo "  (ninguno de los esperados)"
elif command -v netstat &> /dev/null; then
    netstat -tlnp 2>/dev/null | grep -E ":(80|443|8080|8443)" || echo "  (ninguno de los esperados)"
else
    echo "  (ss/netstat no disponible)"
fi

echo ""
echo "Docker daemon info:"
echo "  Usuario: $(whoami)"
echo "  Docker socket: $DOCKER_HOST"
echo ""

# Verificar compose.yaml
if [ -f "compose.yaml" ]; then
    echo "Puertos en compose.yaml actual:"
    grep -E "^[[:space:]]*-[[:space:]]*\"?[0-9]+:" compose.yaml | sed 's/^/  /' || echo "  (no encontrados)"
    echo ""
fi

echo "=================================="
echo "Recomendación"
echo "=================================="
echo ""

if echo "$DOCKER_INFO" | grep -q "rootless"; then
    echo "➜ Ejecuta: ./setup-docker.sh (versión mejorada)"
    echo ""
    echo "  O modifica compose.yaml manualmente:"
    echo "  - Cambiar puerto 443 a 8443"
    echo "  - Cambiar puerto 80 a 8080"
    echo ""
else
    echo "Tu Docker está bien configurado."
    echo "Si sigues viendo errores:"
    echo "  1. Verifica que los puertos no estén en uso"
    echo "  2. Intenta: docker-compose down && docker-compose up -d"
fi
