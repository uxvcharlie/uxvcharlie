"""Tarjetas SVG de repos para el README, en el estilo de la tarjeta neofetch.

Los textos salen de repos.json. Estrellas y última actualización se piden a la API,
pero solo de los repos públicos: el token del Action no puede leer los privados,
así que esos muestran "privado" en vez de estrellas.

Solo usa la librería estándar.

Uso:
    GH_TOKEN=... python repos.py uxvcharlie repos.json -o carpeta_salida/
"""

import argparse
import base64
import json
import os
import textwrap
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

FUENTES = Path(__file__).parent.parent / "fuentes"

ANCHO, ALTO = 410, 150
MARGEN = 20
TAM_TITULO, TAM_TEXTO = 15, 12.5
# La letra mide 0.6 em, pero Chrome en Linux redondea cada avance a píxel entero
# (7.5 px -> 8 px): se calcula con 0.65 para que ninguna línea toque el borde.
LETRAS_POR_LINEA = int((ANCHO - 2 * MARGEN) / (TAM_TEXTO * 0.65))

FONDO = "#0d1117"
GRIS = "#8b949e"
TEXTO = "#c9d1d9"
ROSA = "#f0a8bc"
CLAVE = "#d87492"
# Colores de lenguaje de GitHub (linguist), para que el punto se reconozca.
COLOR_LENGUAJE = {"Rust": "#dea584", "Python": "#3572A5", "JavaScript": "#f1e05a",
                  "Java": "#b07219", "HTML": "#e34c26", "TypeScript": "#3178c6"}
ICONO_REPO, ICONO_CANDADO, ICONO_ESTRELLA = "", "", ""


def api(ruta: str, token: str | None) -> dict | None:
    cabeceras = {"User-Agent": "tarjetas-repos", "Accept": "application/vnd.github+json"}
    if token:
        cabeceras["Authorization"] = f"Bearer {token}"
    try:
        with urllib.request.urlopen(urllib.request.Request(
                f"https://api.github.com{ruta}", headers=cabeceras), timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 404:  # privado o inexistente para este token
            return None
        raise


def hace(cuando: str) -> str:
    dias = (datetime.now(timezone.utc) - datetime.fromisoformat(cuando.replace("Z", "+00:00"))).days
    if dias == 0:
        return "actualizado hoy"
    if dias == 1:
        return "actualizado ayer"
    if dias < 30:
        return f"actualizado hace {dias} días"
    meses = dias // 30
    return f"actualizado hace {meses} {'mes' if meses == 1 else 'meses'}"


def fuente(nombre: str, peso: int) -> str:
    datos = base64.b64encode((FUENTES / nombre).read_bytes()).decode()
    return (f"@font-face{{font-family:J;font-weight:{peso};"
            f"src:url(data:font/woff2;base64,{datos}) format('woff2')}}")


def tarjeta(r: dict, vivo: dict | None) -> str:
    x0 = MARGEN
    piezas = []

    # Título: ícono + ~/nombre
    icono = ICONO_CANDADO if r.get("privado") else ICONO_REPO
    piezas.append(
        f'<text x="{x0}" y="{MARGEN + 16}" font-size="{TAM_TITULO}">'
        f'<tspan fill="{CLAVE}">{icono}</tspan><tspan fill="{GRIS}"> ~/</tspan>'
        f'<tspan fill="{ROSA}" font-weight="700">{escape(r["titulo"])}</tspan></text>')

    # Esquina: estrellas (público) o "privado"
    if r.get("privado"):
        derecha = f'<tspan fill="{GRIS}">privado</tspan>'
    else:
        estrellas = vivo["stargazers_count"] if vivo else 0
        derecha = f'<tspan fill="{CLAVE}">{ICONO_ESTRELLA}</tspan><tspan fill="{TEXTO}"> {estrellas}</tspan>'
    piezas.append(f'<text x="{ANCHO - MARGEN}" y="{MARGEN + 16}" font-size="{TAM_TEXTO}" '
                  f'text-anchor="end">{derecha}</text>')

    # Descripción en hasta 3 líneas
    for i, linea in enumerate(textwrap.wrap(r["descripcion"], LETRAS_POR_LINEA)[:3]):
        piezas.append(f'<text x="{x0}" y="{MARGEN + 46 + i * 18}" font-size="{TAM_TEXTO}" '
                      f'fill="{TEXTO}">{escape(linea)}</text>')

    # Pie: lenguaje · actualizado / nota
    y_pie = ALTO - MARGEN
    lenguaje = r["lenguaje"]
    piezas.append(f'<circle cx="{x0 + 5}" cy="{y_pie - 4}" r="5" '
                  f'fill="{COLOR_LENGUAJE.get(lenguaje, GRIS)}"/>')
    extra = r.get("nota") or (hace(vivo["pushed_at"]) if vivo else "")
    pie = f'<tspan fill="{TEXTO}">{escape(lenguaje)}</tspan>'
    if extra:
        pie += f'<tspan fill="{GRIS}"> · {escape(extra)}</tspan>'
    piezas.append(f'<text x="{x0 + 16}" y="{y_pie}" font-size="{TAM_TEXTO}">{pie}</text>')

    estilo = (fuente("jbm-latin-Regular.woff2", 400) + fuente("jbm-latin-Bold.woff2", 700) +
              "text{font-family:J,'JetBrains Mono',ui-monospace,monospace;white-space:pre}")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{ANCHO}" height="{ALTO}" '
        f'viewBox="0 0 {ANCHO} {ALTO}">\n'
        f'<!-- Fuente: JetBrains Mono, SIL Open Font License 1.1 -->\n'
        f'<title>{escape(r["titulo"])}</title>\n'
        f'<style>{estilo}</style>\n'
        f'<defs><linearGradient id="borde" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="#b0566f"/><stop offset="1" stop-color="#4f3852"/></linearGradient></defs>\n'
        f'<rect x="1" y="1" width="{ANCHO - 2}" height="{ALTO - 2}" rx="10" fill="{FONDO}" '
        f'stroke="url(#borde)" stroke-width="1.5"/>\n'
        + "\n".join(piezas) + "\n</svg>\n"
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("usuario")
    p.add_argument("lista", help="repos.json")
    p.add_argument("-o", "--salida", default=".")
    a = p.parse_args()

    token = os.environ.get("GH_TOKEN")
    salida = Path(a.salida)
    salida.mkdir(parents=True, exist_ok=True)
    for r in json.loads(Path(a.lista).read_text(encoding="utf-8")):
        vivo = None if r.get("privado") else api(f"/repos/{a.usuario}/{r['repo']}", token)
        archivo = salida / f"repo-{r['titulo']}.svg"
        archivo.write_text(tarjeta(r, vivo), encoding="utf-8")
        print(archivo, "(sin datos de la API)" if vivo is None and not r.get("privado") else "")


if __name__ == "__main__":
    main()
