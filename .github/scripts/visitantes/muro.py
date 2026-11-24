"""Dibuja el muro de visitantes (SVG) a partir de firmas.json: las últimas firmas, cada una con
el avatar en ASCII, el usuario y la fecha, en el estilo de las demás tarjetas del README.

Solo usa la librería estándar.

Uso:
    python muro.py firmas.json -o visitantes.svg
"""

import argparse
import base64
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.sax.saxutils import escape

FUENTES = Path(__file__).parent.parent / "fuentes"

ANCHO = 830
MARGEN = 20
POR_FILA, MAX_FIRMAS = 5, 10
HUECO = 14
TAM_ARTE = 10                       # 10 px: cada letra mide 6 px exactos (sin redondeo en Linux)
LETRA, FILA = TAM_ARTE * 0.6, TAM_ARTE * 1.2
ANCHO_FICHA = (ANCHO - 2 * MARGEN - (POR_FILA - 1) * HUECO) / POR_FILA
ALTO_FICHA = 11 * FILA + 46        # 11 filas de arte (22 columnas) + usuario + fecha

FONDO, GRIS, TEXTO, ROSA, CLAVE = "#0d1117", "#8b949e", "#c9d1d9", "#f0a8bc", "#d87492"
MESES = "ene feb mar abr may jun jul ago sep oct nov dic".split()
MANAGUA = timezone(timedelta(hours=-6))


def fuente(nombre: str, peso: int) -> str:
    datos = base64.b64encode((FUENTES / nombre).read_bytes()).decode()
    return (f"@font-face{{font-family:J;font-weight:{peso};"
            f"src:url(data:font/woff2;base64,{datos}) format('woff2')}}")


def fecha_corta(iso: str) -> str:
    f = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(MANAGUA)
    return f"{f.day} {MESES[f.month - 1]}"


def ficha(x: float, y: float, firma: dict) -> str:
    piezas = [f'<rect x="{x:.1f}" y="{y:.1f}" width="{ANCHO_FICHA:.1f}" height="{ALTO_FICHA:.1f}" '
              f'rx="8" fill="#11161d" stroke="#2a1620"/>']
    cols = max(sum(len(t) for t, _ in fila) for fila in firma["arte"])
    x_arte = x + (ANCHO_FICHA - cols * LETRA) / 2
    for f, fila in enumerate(firma["arte"]):
        col = 0
        for t, color in fila:
            if color:
                piezas.append(f'<text class="a" x="{x_arte + col * LETRA:.1f}" '
                              f'y="{y + 10 + (f + 0.8) * FILA:.1f}" fill="#{color}">{escape(t)}</text>')
            col += len(t)
    usuario = firma["usuario"] if len(firma["usuario"]) <= 15 else firma["usuario"][:14] + "…"
    centro = x + ANCHO_FICHA / 2
    piezas.append(f'<text class="u" x="{centro:.1f}" y="{y + ALTO_FICHA - 22:.1f}" text-anchor="middle">'
                  f'<tspan fill="{GRIS}">@</tspan><tspan fill="{ROSA}">{escape(usuario)}</tspan></text>')
    piezas.append(f'<text class="f" x="{centro:.1f}" y="{y + ALTO_FICHA - 8:.1f}" text-anchor="middle" '
                  f'fill="{GRIS}">{fecha_corta(firma["fecha"])}</text>')
    return "".join(piezas)


def construir(firmas: list) -> str:
    recientes = sorted(firmas, key=lambda f: f["fecha"], reverse=True)[:MAX_FIRMAS]
    piezas = []
    y = MARGEN

    # Cabecera: el comando y el total
    piezas.append(f'<text class="c" x="{MARGEN}" y="{y + 12}"><tspan fill="{ROSA}" font-weight="700">~ </tspan>'
                  f'<tspan fill="{GRIS}">$ </tspan><tspan fill="{TEXTO}">tail -n {MAX_FIRMAS} visitantes.log</tspan></text>')
    total = f"{len(firmas)} {'firma' if len(firmas) == 1 else 'firmas'}"
    piezas.append(f'<text class="c" x="{ANCHO - MARGEN}" y="{y + 12}" text-anchor="end" fill="{GRIS}">{total}</text>')
    y += 30

    if recientes:
        for i, firma in enumerate(recientes):
            fila, col = divmod(i, POR_FILA)
            piezas.append(ficha(MARGEN + col * (ANCHO_FICHA + HUECO), y + fila * (ALTO_FICHA + HUECO), firma))
        filas = (len(recientes) + POR_FILA - 1) // POR_FILA
        y += filas * ALTO_FICHA + (filas - 1) * HUECO
    else:
        alto_vacio = 70
        piezas.append(f'<rect x="{MARGEN}" y="{y}" width="{ANCHO - 2 * MARGEN}" height="{alto_vacio}" rx="8" '
                      f'fill="none" stroke="#4a1c2d" stroke-dasharray="4 4"/>')
        piezas.append(f'<text class="c" x="{ANCHO / 2}" y="{y + alto_vacio / 2 + 4}" text-anchor="middle" '
                      f'fill="{GRIS}">visitantes.log está vacío</text>')
        y += alto_vacio

    # Pie: cómo firmar, con cursor
    y += 26
    piezas.append(f'<text class="c" x="{MARGEN}" y="{y}"><tspan fill="{CLAVE}" font-weight="700">→ </tspan>'
                  f'<tspan fill="{TEXTO}">tocá el muro para dejar tu firma</tspan>'
                  f'<tspan fill="{GRIS}"> (un issue que dice "firmar")</tspan></text>')
    alto = round(y + MARGEN)

    estilo = (
        fuente("jbm-latin-Regular.woff2", 400) + fuente("jbm-latin-Bold.woff2", 700) +
        "text{font-family:J,'JetBrains Mono',ui-monospace,monospace;white-space:pre}"
        f".a{{font-size:{TAM_ARTE}px}}.u{{font-size:11px}}.f{{font-size:10px}}.c{{font-size:13px}}"
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{ANCHO}" height="{alto}" viewBox="0 0 {ANCHO} {alto}">\n'
        f'<!-- Fuente: JetBrains Mono, SIL Open Font License 1.1 -->\n'
        f'<title>Muro de visitantes: {len(firmas)} firmas</title>\n'
        f'<style>{estilo}</style>\n'
        f'<defs><linearGradient id="borde" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="#b0566f"/><stop offset="1" stop-color="#4f3852"/></linearGradient></defs>\n'
        f'<rect x="1" y="1" width="{ANCHO - 2}" height="{alto - 2}" rx="10" fill="{FONDO}" '
        f'stroke="url(#borde)" stroke-width="2"/>\n'
        + "\n".join(piezas) + "\n</svg>\n"
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("firmas")
    p.add_argument("-o", "--salida", default="visitantes.svg")
    a = p.parse_args()
    ruta = Path(a.firmas)
    firmas = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else []
    Path(a.salida).write_text(construir(firmas), encoding="utf-8")
    print(f"{a.salida}: {len(firmas)} firmas")


if __name__ == "__main__":
    main()
