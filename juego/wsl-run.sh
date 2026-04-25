#!/bin/bash
# Script para compilar y ejecutar Poker Race en WSL
# Detecta automáticamente la ruta del proyecto

# Obtener el directorio donde está este script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "  Poker Race - WSL Build & Run"
echo "=========================================="

# Verificar que raylib está compilado
RAYLIB_DIR="/mnt/c/Users/aleja/Desktop/claude/RayLib/raylib-6.0"
if [ ! -f "$RAYLIB_DIR/src/libraylib.a" ]; then
    echo "⚠️  Raylib no está compilado. Compilando..."
    
    if [ ! -d "$RAYLIB_DIR" ]; then
        echo "❌ Error: No se encuentra raylib en $RAYLIB_DIR"
        echo "   Descarga raylib-6.0 desde https://github.com/raysan5/raylib/releases"
        echo "   y colócalo en: C:/Users/aleja/Desktop/claude/RayLib/raylib-6.0"
        exit 1
    fi
    
    cd "$RAYLIB_DIR/src"
    make PLATFORM=PLATFORM_DESKTOP
    if [ $? -ne 0 ]; then
        echo "❌ Error compilando raylib"
        exit 1
    fi
    echo "✅ Raylib compilado exitosamente"
    cd "$SCRIPT_DIR"
else
    echo "✅ Raylib ya está compilado"
fi

# Compilar el juego
echo ""
echo "🔨 Compilando Poker Race..."
make clean
make desktop

if [ $? -ne 0 ]; then
    echo "❌ Error compilando el juego"
    exit 1
fi

echo ""
echo "✅ Compilación exitosa!"
echo "🎮 Iniciando Poker Race..."
echo ""

# Ejecutar
./build/poker_race
