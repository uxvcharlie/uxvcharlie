"""Mapa de Nicaragua en ASCII para el README, con un punto parpadeando en Managua.

El contorno (nicaragua.json, 52 puntos) viene de Natural Earth vía world.geo.json, dominio público.
Cada celda se pinta si su centro cae dentro del país; las celdas de la orilla van más claras.
Solo usa la librería estándar.

Uso:
    python mapa.py -o mapa.svg
"""

import argparse
import base64
import json
from pathlib import Path
from xml.sax.saxutils import escape

AQUI = Path(__file__).parent
FUENTES = AQUI.parent / "fuentes"

TAM = 14
LETRA = TAM * 0.6
FILA = TAM * 1.2
MARGEN = 24
COLUMNAS = 58
ANCHO = 930

FONDO = "#0d1117"
GRIS = "#8b949e"
TEXTO = "#e6edf3"
CLAVE = "#d87492"
ROSA = "#f0a8bc"
INTERIOR = "#7a2e48"
ORILLA = "#d87492"

# (nombre, longitud, latitud)
MANAGUA = ("Managua", -86.251, 12.136)
CIUDADES = [("León", -86.878, 12.435), ("Granada", -85.956, 11.930),
            ("Estelí", -86.354, 13.091), ("Bluefields", -83.764, 11.999)]

W, E, S, N = -87.7, -83.1, 10.7, 15.05  # caja del mapa


def dentro(poligono: list, x: float, y: float) -> bool:
    """Trazado de rayo: cuenta cuántas aristas cruza una horizontal hacia la derecha."""
    adentro = False
    for (x1, y1), (x2, y2) in zip(poligono, poligono[1:] + poligono[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            adentro = not adentro
    return adentro


def a_pantalla(lon: float, lat: float, filas: int) -> tuple:
    return (MARGEN + (lon - W) / (E - W) * COLUMNAS * LETRA,
            MARGEN + FILA * 2 + (N - lat) / (N - S) * filas * FILA)


def fuente(nombre: str, peso: int) -> str:
    datos = base64.b64encode((FUENTES / nombre).read_bytes()).decode()
    return (f"@font-face{{font-family:J;font-weight:{peso};"
            f"src:url(data:font/woff2;base64,{datos}) format('woff2')}}")


def mapa() -> str:
    poligono = json.loads((AQUI / "nicaragua.json").read_text())
    # La celda es el doble de alta que de ancha: las filas se reparten según esa proporción.
    filas = round(COLUMNAS * (N - S) / (E - W) * LETRA / FILA)
    celdas = []
    for f in range(filas):
        lat = N - (f + 0.5) / filas * (N - S)
        celdas.append([dentro(poligono, W + (c + 0.5) / COLUMNAS * (E - W), lat) for c in range(COLUMNAS)])

    def vecino_fuera(f, c):
        return any(not (0 <= f + df < filas and 0 <= c + dc < COLUMNAS and celdas[f + df][c + dc])
                   for df, dc in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)))

    piezas = [f'<text x="{MARGEN}" y="{MARGEN + 14}" font-size="{TAM}"><tspan fill="{CLAVE}">uxvcharlie@arch</tspan>'
              f'<tspan fill="{GRIS}">:~$</tspan><tspan fill="{TEXTO}" dx="{LETRA:.1f}">locate managua</tspan></text>']
    for f, fila in enumerate(celdas):
        y = MARGEN + FILA * 2 + (f + 0.8) * FILA
        tramos, actual = [], None
        for c, esta in enumerate(fila):
            clase = None if not esta else ("o" if vecino_fuera(f, c) else "i")
            if actual and actual[0] == clase:
                actual[1] += 1
            else:
                actual = [clase, 1]
                tramos.append(actual)
        x = MARGEN
        for clase, n in tramos:
            if clase:
                color, letra = (ORILLA, "#") if clase == "o" else (INTERIOR, "·")
                piezas.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{TAM}" fill="{color}">{letra * n}</text>')
            x += n * LETRA

    # Ciudades chicas fijas y Managua con pulso.
    for nombre, lon, lat in CIUDADES:
        x, y = a_pantalla(lon, lat, filas)
        piezas.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.2" fill="{ROSA}"/>')
        piezas.append(f'<text x="{x + 6:.1f}" y="{y + 4:.1f}" font-size="10.5" fill="{GRIS}">{escape(nombre)}</text>')
    x, y = a_pantalla(MANAGUA[1], MANAGUA[2], filas)
    piezas.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="none" stroke="{ROSA}" stroke-width="1.5" class="onda"/>')
    piezas.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.6" fill="#fff6f9" class="latido"/>')
    piezas.append(f'<text x="{x + 9:.1f}" y="{y - 6:.1f}" font-size="11.5" fill="{ROSA}" font-weight="700">Managua</text>')

    # Datos a la derecha, como en neofetch.
    x0 = MARGEN + COLUMNAS * LETRA + 40
    datos = [("País", "Nicaragua"), ("Ciudad", "Managua"), ("Coordenadas", "12.14° N, 86.25° O"),
             ("Zona", "UTC−6, sin horario de verano"), ("Altura", "43 m sobre el mar"),
             ("Lagos", "Cocibolca y Xolotlán"), ("Volcanes", "Masaya, Momotombo, Concepción"),
             ("Idioma", "español")]
    for i, (k, v) in enumerate(datos):
        y = MARGEN + FILA * 4 + i * FILA * 1.35
        piezas.append(f'<text x="{x0:.1f}" y="{y:.1f}" font-size="{TAM}"><tspan fill="{CLAVE}" font-weight="700">{k}</tspan>'
                      f'<tspan fill="{GRIS}">:</tspan><tspan fill="{TEXTO}" dx="{LETRA:.1f}">{escape(v)}</tspan></text>')

    alto = int(MARGEN * 2 + FILA * 2 + filas * FILA + 6)
    estilo = (fuente("jbm-latin-Regular.woff2", 400) + fuente("jbm-latin-Bold.woff2", 700) +
              "text{font-family:J,'JetBrains Mono',ui-monospace,monospace;white-space:pre}"
              "@keyframes latido{0%,100%{opacity:1}50%{opacity:.25}}"
              "@keyframes onda{0%{r:4;opacity:.9}100%{r:20;opacity:0}}"
              ".latido{animation:latido 1.6s ease-in-out infinite}"
              ".onda{animation:onda 2.4s ease-out infinite}")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{ANCHO}" height="{alto}" viewBox="0 0 {ANCHO} {alto}">\n'
        f'<!-- Fuente: JetBrains Mono, SIL Open Font License 1.1. Contorno: Natural Earth, dominio público -->\n'
        f'<title>Mapa de Nicaragua con Managua marcada</title>\n<style>{estilo}</style>\n'
        f'<defs><linearGradient id="borde" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="#b0566f"/><stop offset="1" stop-color="#4f3852"/></linearGradient></defs>\n'
        f'<rect x="1" y="1" width="{ANCHO - 2}" height="{alto - 2}" rx="10" fill="{FONDO}" stroke="url(#borde)" stroke-width="1.5"/>\n'
        + "\n".join(piezas) + "\n</svg>\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-o", "--salida", default="mapa.svg")
    Path(p.parse_args().salida).write_text(mapa(), encoding="utf-8")


if __name__ == "__main__":
    main()
