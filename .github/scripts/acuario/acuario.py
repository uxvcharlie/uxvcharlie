"""Acuario del README: cada repo público es un pez, en SVG animado.

- Tamaño del pez = commits del repo.
- Color = su lenguaje principal (el más usado es el más claro).
- Los repos con push reciente nadan de lado a lado; los que llevan más de DIAS_DORMIDO días sin push
  duermen en el fondo, con una "z" que sube.
- El tamaño y el color salen de la API, pero el sitio y la velocidad de cada pez salen de su nombre, no del azar:
  el acuario no se reordena de un día a otro.

Solo cuenta repos públicos sin fork y con lenguaje. Solo usa la librería estándar.

Uso:
    GH_TOKEN=... python acuario.py uxvcharlie -o acuario.svg
"""

import argparse
import base64
import hashlib
import json
import math
import os
import random
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

FUENTES = Path(__file__).parent.parent / "fuentes"

ANCHO, ALTO = 840, 340
FONDO_ARENA = ALTO - 44  # donde empieza la arena
DIAS_DORMIDO = 45
MARGEN = 24

FONDO = "#0d1117"
GRIS = "#8b949e"
TEXTO = "#e6edf3"
CLAVE = "#d87492"
COLORES = ["#f0a8bc", "#d87492", "#b0566f", "#c4607e", "#963858", "#e08aa6"]


def graphql(consulta: str, token: str) -> dict:
    pedido = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": consulta}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "tarjeta-acuario"},
    )
    with urllib.request.urlopen(pedido, timeout=30) as r:
        respuesta = json.load(r)
    if "errors" in respuesta:
        raise SystemExit(f"GraphQL: {respuesta['errors']}")
    return respuesta["data"]


def repos(usuario: str, token: str) -> list:
    nodos = graphql(f'''{{ user(login: "{usuario}") {{
        repositories(ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false, first: 100) {{
          nodes {{ name pushedAt primaryLanguage {{ name }}
            defaultBranchRef {{ target {{ ... on Commit {{ history {{ totalCount }} }} }} }} }} }} }} }}''',
                    token)["user"]["repositories"]["nodes"]
    ahora = datetime.now(timezone.utc)
    salida = []
    for n in nodos:
        if not n["primaryLanguage"] or not n["defaultBranchRef"]:
            continue
        dias = (ahora - datetime.fromisoformat(n["pushedAt"].replace("Z", "+00:00"))).days
        salida.append({"nombre": n["name"], "lenguaje": n["primaryLanguage"]["name"], "dias": dias,
                       "commits": n["defaultBranchRef"]["target"]["history"]["totalCount"]})
    return salida


def azar(texto: str) -> random.Random:
    return random.Random(int(hashlib.sha256(texto.encode()).hexdigest()[:12], 16))


def pez(s: float, color: str, dormido: bool) -> str:
    """Pez mirando a la derecha, centrado en (0,0): cuerpo, cola, aleta y ojo."""
    ojo = f'<path d="M{s * 0.45:.1f},{-s * 0.12:.1f} q{s * 0.12:.1f},{s * 0.1:.1f} {s * 0.24:.1f},0" stroke="#0d1117" stroke-width="1.6" fill="none"/>' \
        if dormido else f'<circle cx="{s * 0.55:.1f}" cy="{-s * 0.1:.1f}" r="{max(1.6, s * 0.1):.1f}" fill="#0d1117"/>'
    return (f'<path d="M{-s * 0.8:.1f},0 L{-s * 1.5:.1f},{-s * 0.55:.1f} L{-s * 1.35:.1f},0 L{-s * 1.5:.1f},{s * 0.55:.1f}Z" fill="{color}" opacity=".85"/>'
            f'<ellipse cx="0" cy="0" rx="{s:.1f}" ry="{s * 0.56:.1f}" fill="{color}"/>'
            f'<path d="M{-s * 0.2:.1f},{-s * 0.5:.1f} Q{s * 0.1:.1f},{-s * 0.95:.1f} {s * 0.35:.1f},{-s * 0.5:.1f}Z" fill="{color}" opacity=".8"/>'
            f'<path d="M{s * 0.05:.1f},{-s * 0.35:.1f} Q{s * 0.18:.1f},0 {s * 0.05:.1f},{s * 0.35:.1f}" stroke="#0d1117" stroke-opacity=".25" stroke-width="1.2" fill="none"/>'
            + ojo)


def fuente(nombre: str, peso: int) -> str:
    datos = base64.b64encode((FUENTES / nombre).read_bytes()).decode()
    return (f"@font-face{{font-family:J;font-weight:{peso};"
            f"src:url(data:font/woff2;base64,{datos}) format('woff2')}}")


def acuario(lista: list) -> str:
    por_lenguaje = {}
    for r in lista:
        por_lenguaje[r["lenguaje"]] = por_lenguaje.get(r["lenguaje"], 0) + 1
    orden = sorted(por_lenguaje, key=lambda l: (-por_lenguaje[l], l))
    color = {l: COLORES[min(i, len(COLORES) - 1)] for i, l in enumerate(orden)}

    piezas, estilos = [], []

    # Burbujas.
    a = azar("burbujas")
    for i in range(16):
        x, r = a.uniform(20, ANCHO - 20), a.uniform(1.5, 4)
        estilos.append(f".b{i}{{animation:sube {a.uniform(6, 12):.1f}s linear {-a.uniform(0, 12):.1f}s infinite}}")
        piezas.append(f'<circle class="b b{i}" cx="{x:.1f}" cy="{FONDO_ARENA}" r="{r:.1f}" fill="none" stroke="#f0a8bc" stroke-opacity=".5"/>')

    # Algas.
    for i, x in enumerate((60, 150, 330, 480, 610, 770)):
        alto = azar(f"alga{i}").uniform(40, 80)
        piezas.append(f'<g transform="translate({x} {FONDO_ARENA + 4})"><path class="alga" style="animation-delay:{-i * 0.8:.1f}s" '
                      f'd="M0,0 q-9,{-alto * 0.25:.0f} 0,{-alto * 0.5:.0f} t0,{-alto * 0.5:.0f}" stroke="#4a1c2d" stroke-width="5" '
                      f'stroke-linecap="round" fill="none"/></g>')

    # Peces. Los despiertos nadan en carriles distintos; los dormidos se acuestan en el fondo.
    despiertos = sorted((r for r in lista if r["dias"] <= DIAS_DORMIDO), key=lambda r: r["nombre"])
    dormidos = sorted((r for r in lista if r["dias"] > DIAS_DORMIDO), key=lambda r: r["nombre"])

    for i, r in enumerate(despiertos):
        az = azar(r["nombre"])
        s = 9 + 3 * math.log2(r["commits"] + 1)
        y = 40 + (i + az.uniform(-0.3, 0.3)) / max(1, len(despiertos)) * (FONDO_ARENA - 90)
        derecha = az.random() < 0.5
        a_, b_ = (-s * 2, ANCHO + s * 2) if derecha else (ANCHO + s * 2, -s * 2)
        dur, retraso = az.uniform(22, 48), -az.uniform(0, 48)
        estilos.append(f".p{i}{{--a:{a_:.0f}px;--b:{b_:.0f}px;animation:nada {dur:.1f}s linear {retraso:.1f}s infinite}}"
                       f".q{i}{{animation:ondea {az.uniform(2, 4):.1f}s ease-in-out {-az.uniform(0, 4):.1f}s infinite}}")
        x0 = az.uniform(60, ANCHO - 60)  # sitio sin animación (por si el visor no la corre)
        forma = pez(s, color[r["lenguaje"]], False)
        volteo = "" if derecha else ' transform="scale(-1 1)"'
        piezas.append(f'<g transform="translate({x0:.0f} {y:.0f})"><g class="p{i}"><g class="q{i}"><g{volteo}>{forma}'
                      f'<title>{escape(r["nombre"])} · {r["commits"]} commits · {r["lenguaje"]}</title></g></g></g></g>')

    for j, r in enumerate(dormidos):
        az = azar(r["nombre"])
        s = 8 + 2.4 * math.log2(r["commits"] + 1)
        x = 40 + (j + 0.5) / max(1, len(dormidos)) * (ANCHO - 80) + az.uniform(-8, 8)
        y = FONDO_ARENA - s * 0.5 - 2
        estilos.append(f".d{j}{{animation:flota {az.uniform(3, 5):.1f}s ease-in-out {-az.uniform(0, 4):.1f}s infinite}}"
                       f".z{j}{{animation:zzz 4s ease-out {-az.uniform(0, 4):.1f}s infinite}}")
        tenue = color[r["lenguaje"]]
        piezas.append(f'<g transform="translate({x:.0f} {y:.0f})"><g class="d{j}"><g transform="rotate({az.uniform(-8, 8):.0f})" opacity=".55">'
                      f'{pez(s, tenue, True)}<title>{escape(r["nombre"])} · duerme hace {r["dias"]} días</title></g>'
                      f'<text class="z{j}" x="{s * 0.7:.0f}" y="{-s * 0.8:.0f}" font-size="11" fill="{GRIS}">z</text></g></g>')

    # Arena y pie.
    piezas.append(f'<rect x="0" y="{FONDO_ARENA}" width="{ANCHO}" height="{ALTO - FONDO_ARENA}" fill="#1a0f15"/>')
    piezas.append(f'<path d="M0,{FONDO_ARENA} q60,-8 120,0 t120,0 t120,0 t120,0 t120,0 t120,0 t120,0 V{FONDO_ARENA + 6} H0Z" fill="#2a1620"/>')
    piezas.append(f'<text x="{MARGEN}" y="{ALTO - 16}" font-size="12" fill="{GRIS}"><tspan fill="{CLAVE}">uxvcharlie@arch</tspan>:~$ '
                  f'acuario --repos · {len(despiertos)} nadando, {len(dormidos)} dormidos (+{DIAS_DORMIDO} días sin push) · tamaño = commits</text>')

    estilo = (fuente("jbm-latin-Regular.woff2", 400) + fuente("jbm-latin-Bold.woff2", 700) +
              "text{font-family:J,'JetBrains Mono',ui-monospace,monospace;white-space:pre}"
              "@keyframes nada{from{transform:translateX(var(--a))}to{transform:translateX(var(--b))}}"
              "@keyframes ondea{0%,100%{transform:translateY(-4px)}50%{transform:translateY(4px)}}"
              "@keyframes flota{0%,100%{transform:translateY(0)}50%{transform:translateY(-2px)}}"
              "@keyframes zzz{0%{transform:translate(0,0);opacity:0}20%{opacity:.9}100%{transform:translate(8px,-18px);opacity:0}}"
              "@keyframes sube{from{transform:translateY(0);opacity:.7}to{transform:translateY(-" + str(FONDO_ARENA - 10) + "px);opacity:0}}"
              "@keyframes mece{0%,100%{transform:skewX(-7deg)}50%{transform:skewX(7deg)}}"
              ".alga{animation:mece 5s ease-in-out infinite}" + "".join(estilos))
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{ANCHO}" height="{ALTO}" viewBox="0 0 {ANCHO} {ALTO}">\n'
        f'<!-- Fuente: JetBrains Mono, SIL Open Font License 1.1 -->\n'
        f'<title>Acuario de repos de uxvcharlie</title>\n<style>{estilo}</style>\n'
        f'<defs><linearGradient id="borde" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#b0566f"/>'
        f'<stop offset="1" stop-color="#4f3852"/></linearGradient>'
        f'<linearGradient id="agua" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1c1018"/>'
        f'<stop offset="1" stop-color="#3a1a28"/></linearGradient>'
        f'<clipPath id="marco"><rect x="1" y="1" width="{ANCHO - 2}" height="{ALTO - 2}" rx="10"/></clipPath></defs>\n'
        f'<rect x="1" y="1" width="{ANCHO - 2}" height="{ALTO - 2}" rx="10" fill="url(#agua)"/>\n'
        f'<g clip-path="url(#marco)">\n' + "\n".join(piezas) + '\n</g>\n'
        f'<rect x="1" y="1" width="{ANCHO - 2}" height="{ALTO - 2}" rx="10" fill="none" stroke="url(#borde)" stroke-width="1.5"/>\n</svg>\n')


def main():
    p = argparse.ArgumentParser()
    p.add_argument("usuario")
    p.add_argument("-o", "--salida", default="acuario.svg")
    a = p.parse_args()
    lista = repos(a.usuario, os.environ["GH_TOKEN"])
    Path(a.salida).write_text(acuario(lista), encoding="utf-8")
    print(f"{len(lista)} peces, {sum(1 for r in lista if r['dias'] > DIAS_DORMIDO)} dormidos")


if __name__ == "__main__":
    main()
