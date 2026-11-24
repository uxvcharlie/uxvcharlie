"""Tarjeta "df -h" del README: los lenguajes de tus repos públicos como discos montados, en SVG.

Cada lenguaje es un "disco": tamaño = bytes de código en GitHub, uso = su parte del total,
montado en = el repo donde más pesa. Solo cuenta repos públicos (el token del Action no ve los privados).
Solo usa la librería estándar.

Uso:
    GH_TOKEN=... python lenguajes.py uxvcharlie -o lenguajes.svg
"""

import argparse
import base64
import json
import os
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

FUENTES = Path(__file__).parent.parent / "fuentes"

TAM = 14
LETRA = TAM * 0.6
FILA = 24
MARGEN = 24
ANCHO = 840
MAXIMO = 6  # filas

FONDO = "#0d1117"
GRIS = "#8b949e"
TEXTO = "#e6edf3"
CLAVE = "#d87492"
ROSA = "#f0a8bc"
# Escala vino, de lo más lleno a lo más vacío: las barras largas son las más claras.
VINO = ["#f0a8bc", "#d87492", "#b0566f", "#963858", "#7a2e48", "#4a1c2d"]
HUECO = "#2a1620"

BARRA = 22  # celdas de la barra


def graphql(consulta: str, token: str) -> dict:
    pedido = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": consulta}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "tarjeta-lenguajes"},
    )
    with urllib.request.urlopen(pedido, timeout=30) as r:
        respuesta = json.load(r)
    if "errors" in respuesta:
        raise SystemExit(f"GraphQL: {respuesta['errors']}")
    return respuesta["data"]


def lenguajes(usuario: str, token: str) -> list:
    """[(lenguaje, bytes, repo donde más pesa)] de mayor a menor."""
    datos = graphql(f'''{{ user(login: "{usuario}") {{
        repositories(ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false, first: 100) {{
          nodes {{ name languages(first: 20, orderBy: {{field: SIZE, direction: DESC}}) {{
            edges {{ size node {{ name }} }} }} }} }} }} }}''', token)["user"]
    total, mejor = {}, {}
    for repo in datos["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            nombre = e["node"]["name"]
            total[nombre] = total.get(nombre, 0) + e["size"]
            if e["size"] > mejor.get(nombre, (0, ""))[0]:
                mejor[nombre] = (e["size"], repo["name"])
    return sorted(((n, b, mejor[n][1]) for n, b in total.items()), key=lambda x: -x[1])


def humano(b: int) -> str:
    if b < 1024:
        return f"{b}B"
    if b < 1024 ** 2:
        return f"{b / 1024:.1f}K"
    return f"{b / 1024 ** 2:.1f}M"


def fuente(nombre: str, peso: int) -> str:
    datos = base64.b64encode((FUENTES / nombre).read_bytes()).decode()
    return (f"@font-face{{font-family:J;font-weight:{peso};"
            f"src:url(data:font/woff2;base64,{datos}) format('woff2')}}")


def tarjeta(filas: list) -> str:
    filas = filas[:MAXIMO]
    suma = sum(b for _, b, _ in filas)  # el % es de lo que se muestra, para que sume 100
    alto = MARGEN * 2 + FILA * (len(filas) + 3)
    # Columnas fijas, medidas en letras.
    cols = {"disco": 0, "tam": 15, "barra": 23, "pct": 23 + BARRA + 1, "monta": 23 + BARRA + 8}
    x = lambda c: MARGEN + cols[c] * LETRA
    piezas = []
    y = MARGEN + 14

    piezas.append(f'<text x="{MARGEN}" y="{y}" font-size="{TAM}"><tspan fill="{CLAVE}">uxvcharlie@arch</tspan>'
                  f'<tspan fill="{GRIS}">:~$</tspan><tspan fill="{TEXTO}" dx="{LETRA:.1f}">df -h --lenguajes</tspan></text>')
    y += FILA + 4
    for c, t in (("disco", "Lenguaje"), ("tam", "Tamaño"), ("barra", "Uso"), ("monta", "Montado en")):
        piezas.append(f'<text x="{x(c)}" y="{y}" font-size="{TAM}" fill="{GRIS}" font-weight="700">{t}</text>')

    for i, (nombre, b, repo) in enumerate(filas):
        y += FILA
        pct = b / suma * 100
        llenas = max(1, round(pct / 100 * BARRA))
        color = VINO[min(i, len(VINO) - 1)]
        piezas.append(f'<text x="{x("disco")}" y="{y}" font-size="{TAM}" fill="{ROSA}" font-weight="700">{escape(nombre)}</text>')
        piezas.append(f'<text x="{x("tam")}" y="{y}" font-size="{TAM}" fill="{TEXTO}">{humano(b)}</text>')
        # Rectángulos y no "█": la fuente recortada no trae ese glifo y la barra saldría más corta.
        ancho = BARRA * LETRA
        piezas.append(f'<rect x="{x("barra")}" y="{y - 12}" width="{ancho:.1f}" height="14" rx="2" fill="{HUECO}"/>')
        piezas.append(f'<rect x="{x("barra")}" y="{y - 12}" width="{ancho * pct / 100:.1f}" height="14" rx="2" fill="{color}"/>')
        piezas.append(f'<text x="{x("pct")}" y="{y}" font-size="{TAM}" fill="{TEXTO}">{pct:4.1f}%</text>')
        piezas.append(f'<text x="{x("monta")}" y="{y}" font-size="{TAM}" fill="{GRIS}">/{escape(repo)}</text>')

    estilo = (fuente("jbm-latin-Regular.woff2", 400) + fuente("jbm-latin-Bold.woff2", 700) +
              "text{font-family:J,'JetBrains Mono',ui-monospace,monospace;white-space:pre}")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{ANCHO}" height="{alto}" viewBox="0 0 {ANCHO} {alto}">\n'
        f'<!-- Fuente: JetBrains Mono, SIL Open Font License 1.1 -->\n'
        f'<title>Lenguajes de uxvcharlie</title>\n<style>{estilo}</style>\n'
        f'<defs><linearGradient id="borde" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="#b0566f"/><stop offset="1" stop-color="#4f3852"/></linearGradient></defs>\n'
        f'<rect x="1" y="1" width="{ANCHO - 2}" height="{alto - 2}" rx="10" fill="{FONDO}" '
        f'stroke="url(#borde)" stroke-width="1.5"/>\n' + "\n".join(piezas) + "\n</svg>\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("usuario")
    p.add_argument("-o", "--salida", default="lenguajes.svg")
    a = p.parse_args()
    filas = lenguajes(a.usuario, os.environ["GH_TOKEN"])
    for f in filas:
        print(f)
    Path(a.salida).write_text(tarjeta(filas), encoding="utf-8")


if __name__ == "__main__":
    main()
