"""Dibuja los logos de Delio y los guarda como SVG.

    python generar_logo.py

Hace dos logos:

1. Logotipo ondulado ("Delio" escrito). Las letras se construyen con
   geometría simple (rectángulos, elipses) y después se pasan por una
   "onda" que mueve cada punto un poco, como si se vieran bajo el agua.
2. Símbolo circular: un aro con una D hecha de una barra y un arco.

Para cambiar qué tan ondulado queda, mueve ONDA_FUERZA y ONDA_LARGO.
"""

import math
from pathlib import Path

AQUI = Path(__file__).parent

COLORES = {"tinta": "#1e1e19", "caqui": "#a0a084"}

# ---------- Medidas de las letras (en unidades propias, y hacia arriba) ----------

ALTO = 100        # altura de la D y la l
ALTO_X = 76       # altura de las minúsculas (e, i, o)
TRAZO = 20        # grosor de los palos verticales
TRAZO_H = 17      # grosor de las partes horizontales (un poco más delgadas)
ESPACIO = 12      # separación entre letras
ESQUINA = 4.5     # radio con que se redondean las esquinas
PASO = 0.8        # distancia entre puntos de un contorno


# ---------- Piezas de contorno: listas de puntos (x, y) ----------

def linea(p, q):
    n = max(1, round(math.dist(p, q) / PASO))
    return [(p[0] + (q[0] - p[0]) * i / n, p[1] + (q[1] - p[1]) * i / n) for i in range(n + 1)]


def arco(cx, cy, rx, ry, a0, a1):
    """Arco de elipse entre dos ángulos en grados. Si a1 > a0 gira contra reloj."""
    n = max(2, round(abs(math.radians(a1 - a0)) * max(rx, ry) / PASO))
    angulos = (math.radians(a0 + (a1 - a0) * i / n) for i in range(n + 1))
    return [(cx + rx * math.cos(a), cy + ry * math.sin(a)) for a in angulos]


def recortar_inicio(puntos, largo):
    """Quita `largo` de recorrido al principio de la pieza."""
    andado = 0.0
    for i in range(1, len(puntos)):
        tramo = math.dist(puntos[i - 1], puntos[i])
        if andado + tramo >= largo:
            f = (largo - andado) / tramo
            corte = (puntos[i - 1][0] + (puntos[i][0] - puntos[i - 1][0]) * f,
                     puntos[i - 1][1] + (puntos[i][1] - puntos[i - 1][1]) * f)
            return [corte] + puntos[i:]
        andado += tramo
    return puntos[-1:]


def recortar_final(puntos, largo):
    return recortar_inicio(puntos[::-1], largo)[::-1]


def contorno(piezas, radios):
    """Une piezas en un contorno cerrado.

    radios[i] es el radio con que se redondea la unión entre la pieza i
    y la siguiente (0 = la unión ya es suave y se deja como está).
    """
    n = len(piezas)
    puntos = []
    for i, pieza in enumerate(piezas):
        radio_antes = radios[i - 1]
        radio_despues = radios[i]
        if radio_antes:
            pieza = recortar_inicio(pieza, radio_antes)
        if radio_despues:
            pieza = recortar_final(pieza, radio_despues)
        puntos += pieza
        if radio_despues:
            # Curva de la esquina: de donde se cortó esta pieza a donde empieza
            # la siguiente, jalada hacia el punto donde estaba el pico.
            pico = piezas[i][-1]
            destino = recortar_inicio(piezas[(i + 1) % n], radio_despues)[0]
            origen = pieza[-1]
            for k in range(1, 8):
                t = k / 8
                puntos.append(((1 - t) ** 2 * origen[0] + 2 * t * (1 - t) * pico[0] + t * t * destino[0],
                               (1 - t) ** 2 * origen[1] + 2 * t * (1 - t) * pico[1] + t * t * destino[1]))
    return puntos


def rectangulo(x0, y0, x1, y1, radio=ESQUINA):
    esquinas = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    piezas = [linea(esquinas[i], esquinas[(i + 1) % 4]) for i in range(4)]
    return contorno(piezas, [radio] * 4)


# ---------- Las letras. Cada una devuelve (lista de contornos, ancho) ----------

def letra_D(x):
    ancho = 84
    c = x + ancho - ALTO / 2            # donde termina lo recto y empieza la panza
    afuera = contorno(
        [linea((x, 0), (c, 0)),
         arco(c, ALTO / 2, ALTO / 2, ALTO / 2, -90, 90),
         linea((c, ALTO), (x, ALTO)),
         linea((x, ALTO), (x, 0))],
        [0, 0, ESQUINA, ESQUINA])
    r = ALTO / 2 - TRAZO_H
    hueco = contorno(
        [linea((x + TRAZO, TRAZO_H), (c, TRAZO_H)),
         arco(c, ALTO / 2, ALTO / 2 - TRAZO, r, -90, 90),
         linea((c, ALTO - TRAZO_H), (x + TRAZO, ALTO - TRAZO_H)),
         linea((x + TRAZO, ALTO - TRAZO_H), (x + TRAZO, TRAZO_H))],
        [0, 0, 3, 3])
    return [afuera, hueco], ancho


def letra_e(x):
    rx, ry = 42, 39.5                   # las redondas rebasan un poco la línea, como en una tipografía
    cx, cy = x + rx, ALTO_X / 2
    rxi, ryi = rx - TRAZO, ry - TRAZO_H
    barra = 6.5                         # media altura de la barra horizontal
    fin = 318                           # ángulo donde termina la cola de la e

    def afuera(grados):
        return (cx + rx * math.cos(math.radians(grados)), cy + ry * math.sin(math.radians(grados)))

    def adentro(grados):
        return (cx + rxi * math.cos(math.radians(grados)), cy + ryi * math.sin(math.radians(grados)))

    # Ángulos donde el borde de abajo de la barra toca la elipse de afuera y la de adentro.
    a_afuera = -math.degrees(math.asin(barra / ry))
    a_adentro = 180 + math.degrees(math.asin(barra / ryi))
    cuerpo = contorno(
        [arco(cx, cy, rx, ry, a_afuera, fin),              # vuelta por fuera
         linea(afuera(fin), adentro(fin)),                 # corte de la cola
         arco(cx, cy, rxi, ryi, fin, a_adentro),           # regreso por dentro, por abajo
         linea(adentro(a_adentro), afuera(a_afuera))],     # borde de abajo de la barra
        [ESQUINA, ESQUINA, 2, 3])

    # El "ojo": el hueco de arriba de la barra.
    a_ojo = math.degrees(math.asin(barra / ryi))
    ojo = contorno(
        [linea(adentro(180 - a_ojo), adentro(a_ojo)),
         arco(cx, cy, rxi, ryi, a_ojo, 180 - a_ojo)],
        [2, 2])
    return [cuerpo, ojo], 2 * rx


def letra_l(x):
    return [rectangulo(x, 0, x + TRAZO, ALTO)], TRAZO


def letra_i(x):
    palo = rectangulo(x, 0, x + TRAZO, ALTO_X)
    punto = arco(x + TRAZO / 2, ALTO_X + 16.5, 11.5, 11.5, 0, 360)[:-1]
    return [palo, punto], TRAZO


def letra_o(x):
    rx, ry = 42, 39.5
    cx, cy = x + rx, ALTO_X / 2
    afuera = arco(cx, cy, rx, ry, 0, 360)[:-1]
    hueco = arco(cx, cy, rx - TRAZO, ry - TRAZO_H, 0, 360)[:-1]
    return [afuera, hueco], 2 * rx


# ---------- La onda ----------

ONDA_FUERZA = 4.2     # cuánto se recorre cada punto, como máximo
ONDA_LARGO = 40       # cada cuántas unidades de altura se repite la onda


def ondular(x, y):
    """Recorre el punto a la izquierda o a la derecha según su altura.

    Es la misma onda seno de la portada del sitio, aplicada de lado:
    cada "renglón" de la letra se desliza un poco, y por eso los bordes
    verticales quedan ondulados y los de arriba y abajo quedan rectos.
    """
    return x + ONDA_FUERZA * math.sin(math.tau * y / ONDA_LARGO), y


# ---------- Salida ----------

def logotipo(color):
    x = 0.0
    letras = []
    for letra in (letra_D, letra_e, letra_l, letra_i, letra_o):
        contornos, ancho = letra(x)
        letras.append(contornos)
        x += ancho + ESPACIO
    ancho_total = x - ESPACIO

    margen = 10
    alto_total = ALTO + 6               # el punto de la i sube un poco más que la D
    caminos = []
    for contornos in letras:
        d = ""
        for puntos in contornos:
            # Se ondula y se voltea el eje y (en SVG la y crece hacia abajo).
            movidos = [ondular(px, py) for px, py in puntos]
            d += "M" + "L".join(f"{px + margen:.1f} {alto_total + margen - py:.1f}" for px, py in movidos) + "Z"
        caminos.append(f'<path d="{d}"/>')

    vista = f"0 0 {ancho_total + 2 * margen:.0f} {alto_total + 2 * margen:.0f}"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vista}" role="img" aria-label="Delio">\n'
            f'<g fill="{color}" fill-rule="evenodd">\n' + "\n".join(caminos) + "\n</g>\n</svg>\n")


def simbolo(color, fondo=None, grosor=9):
    """Aro con una D partida: una barra y un arco. Todo con el mismo grosor."""
    piezas = [
        '<circle cx="60" cy="60" r="52"/>',
        '<path d="M41 36V84"/>',
        '<path d="M55 36a24 24 0 0 1 0 48"/>',
    ]
    base = f'<rect width="120" height="120" fill="{fondo}"/>\n' if fondo else ""
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" role="img" aria-label="Delio">\n'
            + base
            + f'<g fill="none" stroke="{color}" stroke-width="{grosor}">\n' + "\n".join(piezas) + "\n</g>\n</svg>\n")


if __name__ == "__main__":
    for nombre, color in COLORES.items():
        (AQUI / f"delio-logotipo-{nombre}.svg").write_text(logotipo(color), encoding="utf-8")
        (AQUI / f"delio-simbolo-{nombre}.svg").write_text(simbolo(color), encoding="utf-8")
    # Para la pestaña del navegador: el símbolo sobre un cuadro caqui,
    # con el trazo más grueso para que se distinga en 16 pixeles.
    (AQUI / "delio-favicon.svg").write_text(simbolo(COLORES["tinta"], COLORES["caqui"], grosor=12), encoding="utf-8")
    print("Listo:", ", ".join(sorted(p.name for p in AQUI.glob("*.svg"))))
