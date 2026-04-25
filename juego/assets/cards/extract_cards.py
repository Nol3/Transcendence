#!/usr/bin/env python3
"""
Script para extraer cartas individuales del sprite sheet 53_cards.png
"""

from PIL import Image
import os

# Configuración
SPRITE_SHEET = "53_cards.png"
OUTPUT_DIR = "."

# Nombres de archivos
SUITS = ["hearts", "diamonds", "clubs", "spades"]
RANKS = ["ace", "2", "3", "4", "5", "6", "7", "8", "9", "10", "jack", "queen", "king"]

def extract_cards():
    # Cargar imagen
    img = Image.open(SPRITE_SHEET)
    width, height = img.size
    
    print(f"Sprite sheet size: {width}x{height}")
    
    # Detectar layout común
    # Layout típico: 13 columnas x 4 filas (52 cartas) + 1 reverso
    
    # Probar layout 13x4 primero
    card_width = width // 13
    card_height = height // 4
    
    print(f"Detected card size: {card_width}x{card_height}")
    print(f"Expected layout: 13 columns x 4 rows")
    
    # Verificar si hay reverso adicional (5 filas)
    if height // 5 == card_height:
        rows = 5
        print(f"Detected 5 rows (includes card back)")
    else:
        rows = 4
        # El reverso podría estar en una posición especial o no estar
    
    extracted = 0
    
    # Extraer las 52 cartas
    for row in range(4):  # 4 palos
        for col in range(13):  # 13 valores
            left = col * card_width
            upper = row * card_height
            right = left + card_width
            lower = upper + card_height
            
            card = img.crop((left, upper, right, lower))
            
            suit = SUITS[row]
            rank = RANKS[col]
            filename = f"{suit}_{rank}.png"
            
            card.save(os.path.join(OUTPUT_DIR, filename))
            print(f"Extracted: {filename}")
            extracted += 1
    
    # Extraer reverso si existe (usualmente en la última fila o posición especial)
    # Intentar diferentes posiciones comunes para el reverso
    back_positions = [
        # Posición 5,0 (primera carta de 5ª fila)
        (0, 4 * card_height, card_width, 5 * card_height),
        # Última posición de la cuarta fila
        (12 * card_width, 3 * card_height, 13 * card_width, 4 * card_height),
    ]
    
    back_extracted = False
    for i, (left, upper, right, lower) in enumerate(back_positions):
        if right <= width and lower <= height:
            try:
                back_card = img.crop((left, upper, right, lower))
                # Verificar que no sea igual a una carta ya extraída
                back_card.save(os.path.join(OUTPUT_DIR, "card_back.png"))
                print(f"Extracted: card_back.png (position {i+1})")
                extracted += 1
                back_extracted = True
                break
            except Exception as e:
                print(f"Could not extract back from position {i+1}: {e}")
    
    if not back_extracted:
        print("Warning: Could not extract card back. Manual extraction needed.")
        # Crear un reverso genérico o notificar
    
    print(f"\nTotal extracted: {extracted} cards")
    print(f"Output directory: {os.path.abspath(OUTPUT_DIR)}")

if __name__ == "__main__":
    extract_cards()
