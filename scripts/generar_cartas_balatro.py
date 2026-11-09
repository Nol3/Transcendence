"""Compone las cartas de Balatro en PNG completos para la web.

El set extraído del juego (`juego/assets/cards/1.cards/`) es **solo la tinta**: los pips, las
figuras y los índices de las esquinas, sobre fondo transparente. Balatro dibuja aparte el papel
de la carta, el borde y las esquinas redondeadas, así que aquí se recompone: papel del mismo
color que la baraja española del proyecto, borde de tinta y la capa de Balatro encima. Sin este
paso, cambiar el mazo dejaría los pips flotando en la mesa.

Dos cosas de ese set, comprobadas leyendo los píxeles (no el nombre de los ficheros):
  · `clubs_*` son **diamantes** y `diamonds_*` son **tréboles**. Los nombres del extractor están
    cruzados: la forma del pip y el color lo confirman (diamantes naranja y tréboles verdes,
    como en Balatro; corazones rosa y picas azuladas).
  · Los rangos sí están bien: la densidad de pips crece con el número, 2 → 10.

Uso:
    python scripts/generar_cartas_balatro.py
"""
import os

from PIL import Image, ImageDraw, ImageFilter

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIGEN = os.path.join(RAIZ, "juego", "assets", "cards", "1.cards")
SALIDA = os.path.join(RAIZ, "front", "public", "cards", "balatro")

# La carta nativa de Balatro es 71x95; se guarda al doble, como la baraja española (146x194),
# para que en pantallas de alta densidad no se vea blanda.
NATIVO = (71, 95)
ESCALA = 2
DESTINO = (NATIVO[0] * ESCALA, NATIVO[1] * ESCALA)

# Recorte fijo de la tinta dentro de la celda (está centrada, con 6 px de margen).
TINTA_CAJA = (6, 6, 65, 89)
MARGEN = 12  # 6 px nativos, al doble

# Los mismos colores que `generar_baraja_espanola.py`: las dos barajas son del mismo juego.
PAPEL_ARRIBA = (248, 244, 236, 255)
PAPEL_ABAJO = (238, 232, 219, 255)
TINTA = (42, 42, 58, 255)
RADIO = 7

# Ficheros → código de carta del front (`2c`, `Td`, `As`…).
#
# Los palos van **corregidos**: en el set, `clubs_*` son diamantes y `diamonds_*` son tréboles
# (el extractor leyó las filas de la hoja en otro orden). Se comprobó por la forma del pip y por
# el color: diamantes naranja y tréboles verdes, como en Balatro.
PALOS = {"hearts": "h", "diamonds": "c", "clubs": "d", "spades": "s"}
#
# Y los rangos van **desplazados uno**: el fichero `ace` es el 2, el `2` es el 3, … el `9` es el
# 10, el `10` es la J, la `jack` la Q, la `queen` el K y el `king` el **As**. También se comprobó:
# el número de pips de cada fichero sube 2, 3, 4 … hasta 10, y el `king` tiene un único pip
# grande con el color del palo, que es un as.
RANGOS = {"ace": "2", "2": "3", "3": "4", "4": "5", "5": "6", "6": "7", "7": "8", "8": "9",
          "9": "T", "10": "J", "jack": "Q", "queen": "K", "king": "A"}

SUPER = 4  # se dibuja a 4x y se reduce: bordes y esquinas quedan suaves


def _papel_con_gradiente(tam):
    """La carta: rectángulo redondeado con un degradado vertical muy suave."""
    w, h = tam
    base = Image.new("RGBA", (w * SUPER, h * SUPER), (0, 0, 0, 0))
    mascara = Image.new("L", base.size, 0)
    ImageDraw.Draw(mascara).rounded_rectangle(
        (0, 0, base.size[0] - 1, base.size[1] - 1), radius=RADIO * SUPER, fill=255
    )
    degradado = Image.new("RGBA", base.size)
    d = ImageDraw.Draw(degradado)
    alto = base.size[1]
    for y in range(alto):
        t = y / max(1, alto - 1)
        color = tuple(
            round(PAPEL_ARRIBA[i] + (PAPEL_ABAJO[i] - PAPEL_ARRIBA[i]) * t) for i in range(4)
        )
        d.line([(0, y), (base.size[0], y)], fill=color)
    base.paste(degradado, (0, 0), mascara)

    # El borde: se dibuja encima y se recorta con la misma máscara.
    borde = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(borde).rounded_rectangle(
        (1 * SUPER, 1 * SUPER, base.size[0] - 1 - SUPER, base.size[1] - 1 - SUPER),
        radius=RADIO * SUPER,
        outline=TINTA,
        width=2 * SUPER,
    )
    base.alpha_composite(borde)
    return base.resize((w, h), Image.LANCZOS)


def _tinta(nombre):
    """La capa de Balatro recortada y escalada al hueco de la carta."""
    im = Image.open(os.path.join(ORIGEN, nombre)).convert("RGBA")
    recorte = im.crop(TINTA_CAJA)
    ancho = DESTINO[0] - 2 * MARGEN
    alto = DESTINO[1] - 2 * MARGEN
    return recorte.resize((ancho, alto), Image.LANCZOS)


def main():
    os.makedirs(SALIDA, exist_ok=True)
    papel = _papel_con_gradiente(DESTINO)
    hechas = 0
    for fichero in sorted(os.listdir(ORIGEN)):
        if not fichero.endswith(".png") or fichero.endswith("_hc.png"):
            continue
        if fichero in ("default.png", "alto_contraste.png", "card_back.png"):
            continue
        palo, rango = fichero[:-4].split("_", 1)
        if palo not in PALOS or rango not in RANGOS:
            print("  se salta (sin mapear):", fichero)
            continue
        carta = papel.copy()
        carta.alpha_composite(_tinta(fichero), (MARGEN, MARGEN))
        carta.save(os.path.join(SALIDA, f"{RANGOS[rango]}{PALOS[palo]}.png"), optimize=True)
        hechas += 1

    # El dorso viene completo (con su marco), a 92x126: se ajusta al aspecto de la carta.
    dorso = Image.open(os.path.join(ORIGEN, "card_back.png")).convert("RGBA")
    proporcion = DESTINO[1] / DESTINO[0]
    alto = round(dorso.width * proporcion)
    arriba = (dorso.height - alto) // 2
    dorso = dorso.crop((0, arriba, dorso.width, arriba + alto)).resize(DESTINO, Image.LANCZOS)
    dorso.save(os.path.join(SALIDA, "back.png"), optimize=True)

    print(f"{hechas} cartas + dorso en {SALIDA}")


if __name__ == "__main__":
    main()
