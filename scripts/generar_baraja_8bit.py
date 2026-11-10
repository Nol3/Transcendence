"""Genera la baraja francesa a partir del arte 8-bit del juego (`juego/assets/cards/BASIC`).

Las originales son 876×1164 (demasiado para servirlas: 53 ficheros de ~1 MB). Aquí se reescalan a
256×340 en WebP, que es ~3× el tamaño máximo al que se pintan (89×118 en pantalla, ×3 de densidad)
y pesa unas 15 veces menos.

El orden de los ficheros no es evidente y está comprobado en `juego/src/card_textures.c`:

    1-13   corazones   (1 = 2, 2 = 3 … 12 = K, 13 = As)
    14-26  tréboles
    27-39  diamantes
    40-52  picas

Uso:
    python scripts/generar_baraja_8bit.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
ORIGEN = RAIZ / "juego" / "assets" / "cards" / "BASIC"
DESTINO = RAIZ / "front" / "public" / "cards" / "8bit"
DESTINO_ES = RAIZ / "front" / "public" / "cards" / "es8bit"

ANCHO, ALTO = 256, 340

# (primer fichero del grupo, sufijo del palo en el código de carta)
PALOS = [(1, "h"), (14, "c"), (27, "d"), (40, "s")]
# Dentro del grupo: la imagen 1 es el 2 y la 13 el As.
RANGOS = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]

# La baraja española de 40 es la francesa **sin 8, 9 ni 10**: del 1 al 7, y sota, caballo y rey.
# Así que el mismo dibujo sirve, cambiando el nombre del palo y el del rango:
#     oros → diamantes   copas → corazones   espadas → picas   bastos → tréboles
#     1 → As   2-7 → 2-7   10 (sota) → J   11 (caballo) → Q   12 (rey) → K
# Las reglas no cambian: por dentro sigue siendo la carta 10, 11 o 12 de oros.
EQUIVALENCIAS = {
    "1": ("A", "d"), "2": ("2", "d"), "3": ("3", "d"), "4": ("4", "d"),
    "5": ("5", "d"), "6": ("6", "d"), "7": ("7", "d"),
    "10": ("J", "d"), "11": ("Q", "d"), "12": ("K", "d"),
}


def main() -> int:
    if not ORIGEN.is_dir():
        print(f"No encuentro el arte original en {ORIGEN}", file=sys.stderr)
        return 1

    DESTINO.mkdir(parents=True, exist_ok=True)
    generadas = 0

    for primero, palo in PALOS:
        for indice, rango in enumerate(RANGOS):
            origen = ORIGEN / f"8BitDeck{primero + indice}.png"
            if not origen.is_file():
                print(f"Falta {origen.name}", file=sys.stderr)
                return 1
            imagen = Image.open(origen).convert("RGBA").resize((ANCHO, ALTO), Image.LANCZOS)
            imagen.save(DESTINO / f"{rango}{palo}.webp", "WEBP", quality=88, method=6)
            generadas += 1

    dorso = ORIGEN / "card_back.png"
    if dorso.is_file():
        Image.open(dorso).convert("RGBA").resize((ANCHO, ALTO), Image.LANCZOS).save(
            DESTINO / "back.webp", "WEBP", quality=88, method=6
        )
        generadas += 1

    # La misma baraja con los nombres de la española, para los cinco juegos de cartas.
    DESTINO_ES.mkdir(parents=True, exist_ok=True)
    palos_es = {"d": "o", "h": "c", "s": "e", "c": "b"}
    for rango_es, (rango_fr, palo_fr) in EQUIVALENCIAS.items():
        for origen_palo, destino_palo in palos_es.items():
            origen = DESTINO / f"{rango_fr}{origen_palo}.webp"
            if origen.is_file():
                Image.open(origen).save(
                    DESTINO_ES / f"{rango_es}{destino_palo}.webp", "WEBP", quality=88, method=6
                )
    if dorso.is_file():
        Image.open(DESTINO / "back.webp").save(DESTINO_ES / "back.webp", "WEBP", quality=88, method=6)
    generadas += len(list(DESTINO_ES.glob("*.webp")))

    peso = sum(f.stat().st_size for f in DESTINO.glob("*.webp")) / 1024 / 1024
    print(f"{generadas} cartas en {DESTINO} ({peso:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
