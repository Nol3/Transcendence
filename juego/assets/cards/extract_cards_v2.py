#!/usr/bin/env python3
"""
Script mejorado para extraer cartas individuales de sprite sheets
Detecta automáticamente la cuadrícula y centra los recortes
"""

from PIL import Image
import os
import sys

# Configuración
SUITS = ["hearts", "diamonds", "clubs", "spades"]
RANKS = ["ace", "2", "3", "4", "5", "6", "7", "8", "9", "10", "jack", "queen", "king"]

def detect_card_grid(img):
    """Detecta la cuadrícula de cartas en la imagen"""
    width, height = img.size
    
    # Layout típico: 13 columnas × 4-5 filas
    # Intentar detectar automáticamente
    
    # Buscar divisores comunes del ancho para encontrar columnas
    possible_cols = []
    for cols in [13, 10, 12, 14]:
        if width % cols == 0 or width % cols < 10:
            card_w = width // cols
            possible_cols.append((cols, card_w))
    
    # Buscar divisores de la altura para filas
    possible_rows = []
    for rows in [4, 5, 6]:
        if height % rows == 0 or height % rows < 10:
            card_h = height // rows
            possible_rows.append((rows, card_h))
    
    # Seleccionar mejor combinación (preferir 13 cols × 4-5 rows)
    best_cols = 13
    best_rows = 4
    
    for cols, _ in possible_cols:
        if cols == 13:
            best_cols = cols
            break
    
    for rows, _ in possible_rows:
        if rows in [4, 5]:
            best_rows = rows
            break
    
    card_width = width // best_cols
    card_height = height // best_rows
    
    print(f"Detected grid: {best_cols} cols × {best_rows} rows")
    print(f"Card size: {card_width}×{card_height}")
    
    return best_cols, best_rows, card_width, card_height

def extract_cards_from_sheet(sheet_path, output_suffix=""):
    """Extrae cartas de un sprite sheet"""
    
    if not os.path.exists(sheet_path):
        print(f"Error: File not found: {sheet_path}")
        return False
    
    img = Image.open(sheet_path)
    width, height = img.size
    
    print(f"\nProcessing: {sheet_path}")
    print(f"Image size: {width}×{height}")
    
    cols, rows, card_w, card_h = detect_card_grid(img)
    
    # Calcular margen (si existe espacio entre cartas)
    used_width = cols * card_w
    used_height = rows * card_h
    margin_x = (width - used_width) // 2 if width > used_width else 0
    margin_y = (height - used_height) // 2 if height > used_height else 0
    
    print(f"Margins: x={margin_x}, y={margin_y}")
    
    extracted = 0
    
    # Extraer las 52 cartas (4 palos × 13 valores)
    for row in range(4):  # Solo las primeras 4 filas son cartas
        for col in range(13):
            # Calcular posición con margen incluido
            left = margin_x + col * card_w
            upper = margin_y + row * card_h
            right = left + card_w
            lower = upper + card_h
            
            # Validar límites
            if right > width or lower > height:
                print(f"Warning: Card at ({row},{col}) exceeds image bounds")
                continue
            
            # Recortar
            card = img.crop((left, upper, right, lower))
            
            # Generar nombre
            suit = SUITS[row]
            rank = RANKS[col]
            
            if output_suffix:
                filename = f"{suit}_{rank}_{output_suffix}.png"
            else:
                filename = f"{suit}_{rank}.png"
            
            card.save(filename)
            print(f"  Extracted: {filename} ({card_w}×{card_h})")
            extracted += 1
    
    # Extraer reverso (última fila o posición especial)
    back_row = 4 if rows >= 5 else 3
    
    if rows > 4:
        # Hay fila extra, el reverso está allí
        # Buscar carta en posición que parezca reverso (no tenga números/letras típicas)
        # Por simplicidad, tomamos la primera carta de la última fila
        left = margin_x
        upper = margin_y + back_row * card_h
        right = left + card_w
        lower = upper + card_h
        
        if lower <= height:
            back_card = img.crop((left, upper, right, lower))
            
            if output_suffix:
                back_filename = f"card_back_{output_suffix}.png"
            else:
                back_filename = "card_back.png"
            
            back_card.save(back_filename)
            print(f"  Extracted: {back_filename}")
            extracted += 1
    
    print(f"\nTotal extracted: {extracted} cards from {sheet_path}")
    return True

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    print("=" * 60)
    print("Card Extraction Tool v2")
    print("=" * 60)
    
    # Procesar los dos nuevos sprite sheets
    sheets = [
        ("default.png", ""),           # Estándar (sin sufijo)
        ("alto_contraste.png", "hc"),  # Alto contraste (suffix hc)
    ]
    
    for sheet_name, suffix in sheets:
        if os.path.exists(sheet_name):
            extract_cards_from_sheet(sheet_name, suffix)
        else:
            print(f"\nSkipping: {sheet_name} (not found)")
    
    print("\n" + "=" * 60)
    print("Extraction complete!")
    print("=" * 60)
    
    # Listar archivos generados
    print("\nGenerated files:")
    files = [f for f in os.listdir('.') if f.endswith('.png') and f != '53_cards.png']
    for f in sorted(files):
        size = os.path.getsize(f)
        print(f"  {f} ({size} bytes)")

if __name__ == "__main__":
    main()
