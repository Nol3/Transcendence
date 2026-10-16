"""Genera la baraja española del Culo en pixel art, a juego con el mazo del juego.

Mismo tamaño que las cartas del póker (73x97 nativo, guardadas a 146x194) para que las
dos barajas convivan en la misma mesa sin cantar. Se dibuja a mano píxel a píxel: los
palos son sprites de 7x7 y los números una fuente de 3x5, que es lo que da el aire de
8 bits del resto del proyecto.

El 5 de oros se marca aparte (marco dorado y estrella) porque es la carta más alta del
juego: conviene que se vea de un vistazo.
"""
import os
from PIL import Image

NATIVO = (73, 97)
ESCALA = 2
DESTINO = (NATIVO[0] * ESCALA, NATIVO[1] * ESCALA)
SALIDA = r"C:\Users\aleja\Desktop\github\Transcendence\front\public\cards\es"

BLANCO = (244, 240, 230, 255)
TINTA = (42, 42, 58, 255)
ORO = (212, 160, 23, 255)
ORO_CLARO = (242, 201, 76, 255)
ROJO = (176, 48, 42, 255)
ACERO = (91, 107, 140, 255)
VERDE = (63, 125, 63, 255)
FONDO = (0, 0, 0, 0)

# ── Sprites de los palos (7x7). Cada carácter es un color. ────────────────────
PALOS = {
    'o': [  # oros: moneda
        " .OOO. ",
        "OOGGGOO",
        "OGGGGGO",
        "OGGGGGO",
        "OGGGGGO",
        "OOGGGOO",
        " .OOO. ",
    ],
    'c': [  # copas: cáliz
        "RRRRRRR",
        "RRRRRRR",
        ".RRRRR.",
        "..RRR..",
        " ...R..",
        " ...R..",
        " ..RRR.",
    ],
    'e': [  # espadas: hoja con guarnición
        " ...S..",
        " ...S..",
        " ..SSS.",
        " ...S..",
        "SSSSSSS",
        " ...S..",
        " ..SSS.",
    ],
    'b': [  # bastos: palo nudoso
        "....VV.",
        "...VV..",
        "..VVV..",
        ".VVV...",
        "VVV....",
        "VV..V..",
        "V....V.",
    ],
}
COLORES = {'O': ORO, 'G': ORO_CLARO, 'R': ROJO, 'S': ACERO, 'V': VERDE}

# ── Fuente de 3x5 para los índices ───────────────────────────────────────────
DIGITOS = {
    '1': [".#.", "##.", ".#.", ".#.", "##."],
    '2': ["##.", "..#", ".#.", "#..", "###"],
    '3': ["##.", "..#", ".#.", "..#", "##."],
    '4': ["#.#", "#.#", "###", "..#", "..#"],
    '5': ["###", "#..", "##.", "..#", "##."],
    '6': ["##.", "#..", "###", "#.#", "###"],
    '7': ["###", "..#", ".#.", ".#.", ".#."],
    'S': ["###", "#..", "###", "..#", "###"],  # Sota
    'C': ["###", "#..", "#..", "#..", "###"],  # Caballo
    'R': ["##.", "#.#", "##.", "#.#", "#.#"],  # Rey
}


def pintar(im, x, y, sprite, colores, k=1):
    """Pinta un sprite de texto píxel a píxel (cada píxel, un bloque de k x k)."""
    for fy, fila in enumerate(sprite):
        for fx, ch in enumerate(fila):
            if ch in colores:   # el espacio y el punto son «nada que pintar»
                for dy in range(k):
                    for dx in range(k):
                        im.putpixel((x + fx * k + dx, y + fy * k + dy), colores[ch])


def cara_redondeada(im, color, borde):
    """Carta con las esquinas recortadas, como una carta de verdad."""
    w, h = im.size
    for y in range(h):
        for x in range(w):
            en_esquina = (x < 2 or x >= w - 2) and (y < 2 or y >= h - 2)
            if en_esquina:
                im.putpixel((x, y), FONDO)
            elif x == 0 or y == 0 or x == w - 1 or y == h - 1:
                im.putpixel((x, y), borde)
            else:
                im.putpixel((x, y), color)


# Posiciones de los pips por cantidad (centro de la carta a 73x97).
CENTRO = (36, 48)
POSICIONES = {
    1: [(0, 0)],
    2: [(0, -26), (0, 26)],
    3: [(0, -30), (0, 0), (0, 30)],
    4: [(-19, -24), (19, -24), (-19, 24), (19, 24)],
    5: [(-19, -26), (19, -26), (0, 0), (-19, 26), (19, 26)],
    6: [(-19, -28), (19, -28), (-19, 0), (19, 0), (-19, 28), (19, 28)],
    7: [(-19, -30), (19, -30), (-19, -10), (19, -10), (0, 2), (-19, 22), (19, 22)],
}
RANGOS = [1, 2, 3, 4, 5, 6, 7, 10, 11, 12]
ETIQUETA = {10: 'S', 11: 'C', 12: 'R'}


def carta(suit, rank):
    im = Image.new("RGBA", NATIVO, FONDO)
    especial = rank == 5 and suit == 'o'
    cara_redondeada(im, BLANCO, ORO if especial else TINTA)

    # Índice de la esquina: número (o letra de figura) y el palo debajo.
    etiqueta = ETIQUETA.get(rank, str(rank))
    pintar(im, 5, 6, DIGITOS[etiqueta], {'#': TINTA})
    pintar(im, 4, 14, PALOS[suit], COLORES)

    if rank <= 7:
        for dx, dy in POSICIONES[rank]:
            # -7 = medio pip (el sprite mide 7 y se pinta al doble)
            pintar(im, CENTRO[0] + dx - 7, CENTRO[1] + dy - 7, PALOS[suit], COLORES, k=2)
    else:
        # Figuras: una silueta sencilla (cabeza y cuerpo) en el color del palo.
        color = next(COLORES[ch] for fila in PALOS[suit] for ch in fila if ch in COLORES)
        pintar(im, 26, 26, ["..###..", ".#####.", ".#####.", "..###.."], {'#': color}, k=2)
        pintar(im, 22, 36, ["#########", "#########", "#########", "#########",
                            "###...###", "###...###", "###...###"], {'#': color}, k=2)
        # Y el palo, pequeño, para saber de cuál es la figura.
        pintar(im, 60, 80, PALOS[suit], COLORES)

    if especial:
        # El 5 de oros: la carta más alta del juego, marcada para que se vea.
        pintar(im, 33, 12, ["..###..", ".#####.", "###.###", "##...#.", "##..#..",
                            "##.#...", "###.###"], {'#': ORO})
        for x in range(6, 67):
            im.putpixel((x, 3), ORO)
            im.putpixel((x, 93), ORO)

    return im.resize(DESTINO, Image.NEAREST)


def main():
    os.makedirs(SALIDA, exist_ok=True)
    hechas = 0
    for suit in "oceb":
        for rank in RANGOS:
            codigo = f"{rank}{suit}"
            carta(suit, rank).save(os.path.join(SALIDA, f"{codigo}.png"), "PNG", optimize=True)
            hechas += 1
    # Dorso: el mismo que el del póker, para no mezclar estilos en la mesa.
    print(f"cartas españolas generadas: {hechas} en {SALIDA}")
    peso = sum(os.path.getsize(os.path.join(SALIDA, f)) for f in os.listdir(SALIDA))
    print(f"peso total: {peso / 1024:.0f} KB")


if __name__ == '__main__':
    main()
