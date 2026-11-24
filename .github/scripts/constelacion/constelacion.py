"""Constelación de repos para el README: cada repo público es una estrella, en SVG.

- Cada lenguaje principal es una constelación: sus repos quedan juntos y unidos por líneas.
- El tamaño de la estrella sale de los commits del repo (más commits, más grande y más brillante).
- Una línea punteada une constelaciones cuando un repo usa un segundo lenguaje (HTML dentro de TypeScript, etc.).
- Las posiciones salen del nombre del repo, no del azar: el cielo no cambia de un día a otro, solo
  cuando aparece un repo nuevo o cambian los commits.

Solo cuenta repos públicos sin fork y con lenguaje (el token del Action no ve los privados).
Solo usa la librería estándar.

Uso:
    GH_TOKEN=... python constelacion.py uxvcharlie -o constelacion.svg
"""

import argparse
import base64
import hashlib
import json
import math
import os
import random
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

FUENTES = Path(__file__).parent.parent / "fuentes"

ANCHO, ALTO = 840, 400
FONDO = "#0d1117"
GRIS = "#8b949e"
TEXTO = "#e6edf3"
ROSA = "#f0a8bc"
VINO = ["#f0a8bc", "#d87492", "#b0566f", "#963858", "#7a2e48"]  # una por constelación, de la más grande a la más chica
# Sitio de cada constelación, de la más grande a la más chica: (x, y).
SITIOS = [(230, 200), (690, 185), (530, 100), (520, 285), (730, 310), (430, 60), (120, 70)]
DISTANCIA_MINIMA = 40


def graphql(consulta: str, token: str) -> dict:
    pedido = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": consulta}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "tarjeta-constelacion"},
    )
    with urllib.request.urlopen(pedido, timeout=30) as r:
        respuesta = json.load(r)
    if "errors" in respuesta:
        raise SystemExit(f"GraphQL: {respuesta['errors']}")
    return respuesta["data"]


def repos(usuario: str, token: str) -> list:
    nodos = graphql(f'''{{ user(login: "{usuario}") {{
        repositories(ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false, first: 100) {{
          nodes {{ name primaryLanguage {{ name }}
            languages(first: 5, orderBy: {{field: SIZE, direction: DESC}}) {{ edges {{ node {{ name }} }} }}
            defaultBranchRef {{ target {{ ... on Commit {{ history {{ totalCount }} }} }} }} }} }} }} }}''',
                    token)["user"]["repositories"]["nodes"]
    salida = []
    for n in nodos:
        if not n["primaryLanguage"] or not n["defaultBranchRef"]:
            continue  # sin lenguaje (solo docs) o vacío: no es una estrella
        salida.append({
            "nombre": n["name"],
            "lenguaje": n["primaryLanguage"]["name"],
            "otros": [e["node"]["name"] for e in n["languages"]["edges"] if e["node"]["name"] != n["primaryLanguage"]["name"]],
            "commits": n["defaultBranchRef"]["target"]["history"]["totalCount"],
        })
    return salida


def semilla(texto: str) -> random.Random:
    return random.Random(int(hashlib.sha256(texto.encode()).hexdigest()[:12], 16))


def colocar(grupo: list, centro: tuple) -> None:
    """Pone las estrellas de una constelación alrededor de su centro sin que se toquen."""
    radio = 22 * math.sqrt(len(grupo)) + 14
    puestas = []
    for r in sorted(grupo, key=lambda r: r["nombre"]):
        azar = semilla(r["nombre"])
        for intento in range(400):
            ang, dist = azar.uniform(0, 2 * math.pi), radio * math.sqrt(azar.random())
            x, y = centro[0] + dist * math.cos(ang), centro[1] + dist * math.sin(ang) * 0.8
            x, y = min(ANCHO - 40, max(40, x)), min(ALTO - 50, max(45, y))
            minimo = DISTANCIA_MINIMA - intento * 0.06  # si no cabe, se aprieta un poco
            if all(math.hypot(x - px, y - py) >= minimo for px, py in puestas):
                break
        r["x"], r["y"] = x, y
        puestas.append((x, y))


def arbol(grupo: list) -> list:
    """Líneas de la constelación: árbol de distancia mínima (Prim), sin ciclos."""
    if len(grupo) < 2:
        return []
    dentro, fuera, lineas = [grupo[0]], list(grupo[1:]), []
    while fuera:
        a, b = min(((a, b) for a in dentro for b in fuera), key=lambda p: math.hypot(p[0]["x"] - p[1]["x"], p[0]["y"] - p[1]["y"]))
        lineas.append((a, b))
        dentro.append(b)
        fuera.remove(b)
    return lineas


def estrella(x: float, y: float, s: float) -> str:
    """Destello de 4 puntas con lados curvos hacia adentro."""
    return (f"M{x:.1f},{y - s:.1f} Q{x:.1f},{y:.1f} {x + s:.1f},{y:.1f} Q{x:.1f},{y:.1f} {x:.1f},{y + s:.1f} "
            f"Q{x:.1f},{y:.1f} {x - s:.1f},{y:.1f} Q{x:.1f},{y:.1f} {x:.1f},{y - s:.1f}Z")


def fuente(nombre: str, peso: int) -> str:
    datos = base64.b64encode((FUENTES / nombre).read_bytes()).decode()
    return (f"@font-face{{font-family:J;font-weight:{peso};"
            f"src:url(data:font/woff2;base64,{datos}) format('woff2')}}")


def cielo(lista: list) -> str:
    grupos = {}
    for r in lista:
        grupos.setdefault(r["lenguaje"], []).append(r)
    orden = sorted(grupos, key=lambda l: (-len(grupos[l]), l))[:len(SITIOS)]
    color = {l: VINO[min(i, len(VINO) - 1)] for i, l in enumerate(orden)}
    for l, sitio in zip(orden, SITIOS):
        colocar(grupos[l], sitio)
    visibles = [r for l in orden for r in grupos[l]]
    por_nombre = {r["nombre"]: r for r in visibles}

    piezas = []
    # Polvo de estrellas de fondo: fijo, y unas pocas titilan.
    azar = semilla("fondo")
    for i in range(110):
        x, y, r = azar.uniform(8, ANCHO - 8), azar.uniform(8, ALTO - 8), azar.choice([0.6, 0.8, 1.0, 1.3])
        clase = f' class="t{i % 3}"' if i % 4 == 0 else ""
        piezas.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="#c9a9b8" opacity="{azar.uniform(0.25, 0.6):.2f}"{clase}/>')

    # Líneas: constelaciones (continuas) y puentes entre lenguajes (punteadas).
    for l in orden:
        for a, b in arbol(grupos[l]):
            piezas.append(f'<line x1="{a["x"]:.1f}" y1="{a["y"]:.1f}" x2="{b["x"]:.1f}" y2="{b["y"]:.1f}" '
                          f'stroke="{color[l]}" stroke-opacity="0.45" stroke-width="1"/>')
    for r in visibles:
        for otro in r["otros"]:
            destino = next((q for q in grupos.get(otro, []) if q["lenguaje"] == otro and q is not r), None)
            if destino and "x" in destino:
                piezas.append(f'<line x1="{r["x"]:.1f}" y1="{r["y"]:.1f}" x2="{destino["x"]:.1f}" y2="{destino["y"]:.1f}" '
                              f'stroke="#6e5a68" stroke-opacity="0.55" stroke-width="1" stroke-dasharray="3 5"/>')

    # Estrellas. Los textos se reparten sin pisarse: primero el nombre de cada constelación,
    # luego los repos en el primer lado libre (derecha, izquierda, abajo, arriba) o sin texto si no cabe.
    ocupado = []

    def libre(caja):
        return (caja[0] >= 6 and caja[2] <= ANCHO - 6 and caja[1] >= 6 and caja[3] <= ALTO - 36 and
                all(caja[2] < o[0] or caja[0] > o[2] or caja[3] < o[1] or caja[1] > o[3] for o in ocupado))

    for r in visibles:  # las estrellas también ocupan lugar
        ocupado.append((r["x"] - 9, r["y"] - 9, r["x"] + 9, r["y"] + 9))

    nombres = []
    for l in orden:
        n = len(grupos[l])
        texto = f"{l} · {n} {'estrella' if n == 1 else 'estrellas'}"
        ancho = len(texto) * 7.2
        x = min(max(sum(r["x"] for r in grupos[l]) / n, ancho / 2 + 12), ANCHO - ancho / 2 - 12)
        base = max(r["y"] for r in grupos[l])
        # Probar posiciones a distancia creciente, debajo y luego arriba; si ninguna sirve, queda la primera.
        candidatas = [base + 38 + 8 * k for k in range(8)] + [min(r["y"] for r in grupos[l]) - 30 - 8 * k for k in range(6)]
        y = next((c for c in candidatas if libre((x - ancho / 2, c - 12, x + ancho / 2, c + 4))), candidatas[0])
        ocupado.append((x - ancho / 2, y - 12, x + ancho / 2, y + 4))
        nombres.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="12" fill="{color[l]}" text-anchor="middle" font-weight="700">'
                       f'{escape(l)} <tspan fill="{GRIS}" font-weight="400">· {n} {"estrella" if n == 1 else "estrellas"}</tspan></text>')

    mas_commits = sorted(visibles, key=lambda r: -r["commits"])[:6]
    for r in visibles:
        s = 5 + 2.2 * math.log2(r["commits"] + 1)
        c = color[r["lenguaje"]]
        piezas.append(f'<circle cx="{r["x"]:.1f}" cy="{r["y"]:.1f}" r="{s * 1.8:.1f}" fill="url(#brillo-{c[1:]})" opacity="0.55"/>')
        piezas.append(f'<path d="{estrella(r["x"], r["y"], s)}" fill="{c}"><title>{escape(r["nombre"])} · {r["commits"]} commits</title></path>')
        piezas.append(f'<circle cx="{r["x"]:.1f}" cy="{r["y"]:.1f}" r="1.6" fill="#fff6f9"/>')
        if r in mas_commits or r["lenguaje"] != "Java":
            w = len(r["nombre"]) * 6.7
            for dx, dy, ancla in ((s + 5, 4, "start"), (-s - 5, 4, "end"), (0, s + 15, "middle"), (0, -s - 7, "middle")):
                x0 = r["x"] + dx - (w if ancla == "end" else w / 2 if ancla == "middle" else 0)
                caja = (x0, r["y"] + dy - 11, x0 + w, r["y"] + dy + 3)
                if libre(caja):
                    ocupado.append(caja)
                    piezas.append(f'<text x="{r["x"] + dx:.1f}" y="{r["y"] + dy:.1f}" font-size="11" fill="{GRIS}" '
                                  f'text-anchor="{ancla}">{escape(r["nombre"])}</text>')
                    break
    piezas.extend(nombres)
    piezas.append(f'<text x="24" y="{ALTO - 20}" font-size="12" fill="{GRIS}">'
                  f'<tspan fill="#d87492">uxvcharlie@arch</tspan>:~$ stars --constelaciones · {len(visibles)} repos, tamaño = commits</text>')

    brillos = "".join(
        f'<radialGradient id="brillo-{c[1:]}"><stop offset="0" stop-color="{c}" stop-opacity="0.9"/>'
        f'<stop offset="1" stop-color="{c}" stop-opacity="0"/></radialGradient>' for c in VINO)
    estilo = (fuente("jbm-latin-Regular.woff2", 400) + fuente("jbm-latin-Bold.woff2", 700) +
              "text{font-family:J,'JetBrains Mono',ui-monospace,monospace;white-space:pre}"
              "@keyframes t{0%,100%{opacity:.15}50%{opacity:.8}}"
              ".t0{animation:t 4s ease-in-out infinite}.t1{animation:t 6s ease-in-out -2s infinite}"
              ".t2{animation:t 5s ease-in-out -4s infinite}")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{ANCHO}" height="{ALTO}" viewBox="0 0 {ANCHO} {ALTO}">\n'
        f'<!-- Fuente: JetBrains Mono, SIL Open Font License 1.1 -->\n'
        f'<title>Constelación de repos de uxvcharlie</title>\n<style>{estilo}</style>\n'
        f'<defs><linearGradient id="borde" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="#b0566f"/><stop offset="1" stop-color="#4f3852"/></linearGradient>'
        f'<radialGradient id="niebla" cx="0.3" cy="0.5" r="0.7"><stop offset="0" stop-color="#2a1620" stop-opacity="0.9"/>'
        f'<stop offset="1" stop-color="{FONDO}" stop-opacity="0"/></radialGradient>{brillos}</defs>\n'
        f'<rect x="1" y="1" width="{ANCHO - 2}" height="{ALTO - 2}" rx="10" fill="{FONDO}" stroke="url(#borde)" stroke-width="1.5"/>\n'
        f'<rect x="1" y="1" width="{ANCHO - 2}" height="{ALTO - 2}" rx="10" fill="url(#niebla)"/>\n'
        + "\n".join(piezas) + "\n</svg>\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("usuario")
    p.add_argument("-o", "--salida", default="constelacion.svg")
    a = p.parse_args()
    lista = repos(a.usuario, os.environ["GH_TOKEN"])
    Path(a.salida).write_text(cielo(lista), encoding="utf-8")
    print(f"{len(lista)} estrellas")


if __name__ == "__main__":
    main()
