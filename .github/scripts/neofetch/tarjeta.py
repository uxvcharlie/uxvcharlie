"""Tarjeta estilo fastfetch para el README: arte ASCII + datos vivos de GitHub, en SVG.

Solo usa la librería estándar, así corre en el Action sin instalar nada.
El arte sale de arte.py y las fuentes son JetBrains Mono (OFL) recortadas a ASCII.

Uso:
    GH_TOKEN=... python tarjeta.py uxvcharlie --arte arte-avatar-vino.json -o neofetch.svg
"""

import argparse
import base64
import json
import os
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from xml.sax.saxutils import escape

AQUI = Path(__file__).parent

# Medidas: JetBrains Mono mide 0.6 de ancho; el interlineado de 1.2 es el que espera arte.py.
TAM = 14
ANCHO_LETRA = TAM * 0.6
ALTO_FILA = TAM * 1.2
MARGEN = 24

FONDO = "#0d1117"
GRIS = "#8b949e"
TEXTO = "#e6edf3"
CLAVE = "#d87492"
ROSA = "#f0a8bc"
BLOQUES = ["#2a1620", "#4a1c2d", "#7a2e48", "#963858", "#b0566f", "#d87492", "#f0a8bc", "#f6d6df"]


# ---------- datos de GitHub ----------

def graphql(consulta: str, token: str) -> dict:
    pedido = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": consulta}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "tarjeta-neofetch"},
    )
    with urllib.request.urlopen(pedido, timeout=30) as r:
        respuesta = json.load(r)
    if "errors" in respuesta:
        raise SystemExit(f"GraphQL: {respuesta['errors']}")
    return respuesta["data"]


def datos_github(usuario: str, token: str) -> dict:
    base = graphql(f'''{{ user(login: "{usuario}") {{
        createdAt
        repositories(ownerAffiliations: OWNER, privacy: PUBLIC, first: 100) {{
          totalCount nodes {{ stargazerCount }} }} }} }}''', token)["user"]

    # contributionsCollection acepta como mucho un año por consulta: una ventana por año de cuenta.
    creada = datetime.fromisoformat(base["createdAt"].replace("Z", "+00:00"))
    ahora = datetime.now(timezone.utc)
    ventanas, desde = [], creada
    while desde < ahora:
        hasta = min(desde + timedelta(days=365), ahora)
        ventanas.append((desde, hasta))
        desde = hasta
    partes = "\n".join(
        f'v{i}: contributionsCollection(from: "{d.isoformat()}", to: "{h.isoformat()}") '
        f'{{ totalCommitContributions contributionCalendar {{ totalContributions }} }}'
        for i, (d, h) in enumerate(ventanas))
    anios = graphql(f'{{ user(login: "{usuario}") {{ {partes} }} }}', token)["user"]

    return {
        "creada": creada.date().isoformat(),
        "repos": base["repositories"]["totalCount"],
        "estrellas": sum(n["stargazerCount"] for n in base["repositories"]["nodes"]),
        "commits": sum(v["totalCommitContributions"] for v in anios.values()),
        "contribuciones": sum(v["contributionCalendar"]["totalContributions"] for v in anios.values()),
    }


def tiempo_desde(inicio: date, hoy: date) -> str:
    """'1 year, 6 months, 15 days', como el Uptime de fastfetch pero con la edad de la cuenta."""
    meses = (hoy.year - inicio.year) * 12 + hoy.month - inicio.month
    if hoy.day < inicio.day:
        meses -= 1
    y, m = divmod(meses, 12)
    ancla_y, ancla_m = inicio.year + (inicio.month - 1 + meses) // 12, (inicio.month - 1 + meses) % 12 + 1
    dias = (hoy - date(ancla_y, ancla_m, min(inicio.day, 28))).days
    partes = [(y, "year"), (m, "month"), (dias, "day")]
    return ", ".join(f"{n} {txt}{'s' if n != 1 else ''}" for n, txt in partes if n)


# ---------- SVG ----------

def fuente(nombre: str, peso: int) -> str:
    datos = base64.b64encode((AQUI / nombre).read_bytes()).decode()
    return (f"@font-face{{font-family:J;font-weight:{peso};"
            f"src:url(data:font/woff2;base64,{datos}) format('woff2')}}")


def texto(col: float, fila: int, tramos: list[tuple[str, str, bool]], retraso: float) -> str:
    """Una línea en (col, fila) hecha de tramos (texto, color, negrita) que aparece tras `retraso` s."""
    x, y = MARGEN + col * ANCHO_LETRA, MARGEN + (fila + 0.8) * ALTO_FILA
    negrita = ' font-weight="700"'
    spans = "".join(
        f'<tspan fill="{c}"{negrita if b else ""}>{escape(t)}</tspan>' for t, c, b in tramos)
    return f'<text x="{x:.1f}" y="{y:.1f}" style="animation-delay:{retraso:.2f}s">{spans}</text>'


def construir(usuario: str, kernel: str, arte: list, d: dict) -> str:
    filas_arte = len(arte)
    cols_arte = max(sum(len(t) for t, _ in fila) for fila in arte)
    col_info = cols_arte + 3
    piezas = []

    # Arranque tipo systemd con datos reales; al terminar se borra y empieza fastfetch.
    ok = [("[  ", GRIS, False), ("OK", CLAVE, True), ("  ] ", GRIS, False)]
    arranque = [
        [("Welcome to ", TEXTO, False), ("Arch Linux", ROSA, True), ("!", TEXTO, False)],
        [],
        ok + [("Started ", TEXTO, False), (f"{usuario}.service", ROSA, False), (".", TEXTO, False)],
        ok + [("Mounted ", TEXTO, False), (f"/home/{usuario}/proyectos", ROSA, False),
              (f" ({d['repos']}).", TEXTO, False)],
        ok + [("Reached target ", TEXTO, False), ("contributions", ROSA, False),
              (f" ({d['contribuciones']:,}).", TEXTO, False)],
        ok + [("Started ", TEXTO, False), ("nave.service", ROSA, False), (".", TEXTO, False)],
        ok + [("Started ", TEXTO, False), ("spotify.service", ROSA, False), (".", TEXTO, False)],
        ok + [("Listening on ", TEXTO, False), ("visitantes.socket", ROSA, False), (".", TEXTO, False)],
        ok + [("Reached target ", TEXTO, False), ("multi-user.target", ROSA, False), (".", TEXTO, False)],
    ]
    lineas = [texto(0, i, linea, 0.15 + i * 0.13) for i, linea in enumerate(arranque) if linea]
    fin_arranque = 0.15 + len(arranque) * 0.13 + 0.55
    piezas.append(f'<g class="boot" style="animation-delay:{fin_arranque:.2f}s">' + "".join(lineas) + "</g>")

    # Línea 0: el comando, letra por letra.
    inicio = fin_arranque + 0.3
    piezas.append(texto(0, 0, [("~ ", ROSA, True), ("$ ", GRIS, False)], inicio))
    for i, letra in enumerate("fastfetch"):
        piezas.append(texto(4 + i, 0, [(letra, TEXTO, False)], inicio + 0.25 + i * 0.06))
    salida = inicio + 0.25 + 9 * 0.06 + 0.25

    # Arte: cada tramo con su color, en su columna (los espacios no se dibujan).
    for f, fila in enumerate(arte):
        col = 0
        for t, color in fila:
            if color:
                piezas.append(texto(col, f + 2, [(t, f"#{color}", False)], salida + f * 0.012))
            col += len(t)

    info = [
        [(usuario, ROSA, True), ("@", TEXTO, False), ("arch", ROSA, True)],
        [("-" * (len(usuario) + 5), GRIS, False)],
        [("OS", CLAVE, True), (": Arch Linux x86_64", TEXTO, False)],
        [("Kernel", CLAVE, True), (f": {kernel}", TEXTO, False)],
        [("Uptime", CLAVE, True), (f": {tiempo_desde(date.fromisoformat(d['creada']), date.today())}", TEXTO, False)],
        [("Repos", CLAVE, True), (f": {d['repos']}", TEXTO, False), (" · ", GRIS, False),
         ("Stars", CLAVE, True), (f": {d['estrellas']}", TEXTO, False)],
        [("Commits", CLAVE, True), (f": {d['commits']:,}", TEXTO, False)],
        [("Contributions", CLAVE, True), (f": {d['contribuciones']:,}", TEXTO, False)],
        [],
    ]
    arriba = 2 + (filas_arte - len(info) - 1) // 2
    for i, linea in enumerate(info):
        if linea:
            piezas.append(texto(col_info, arriba + i, linea, salida + 0.1 + i * 0.05))
    # Los cuadritos de colores del final de fastfetch, con la paleta vino.
    fila_bloques = arriba + len(info)
    for i, color in enumerate(BLOQUES):
        x = MARGEN + (col_info + i * 3) * ANCHO_LETRA
        y = MARGEN + fila_bloques * ALTO_FILA + 2
        piezas.append(f'<rect class="b" x="{x:.1f}" y="{y:.1f}" width="{3 * ANCHO_LETRA:.1f}" '
                      f'height="{ALTO_FILA - 4:.1f}" fill="{color}" '
                      f'style="animation-delay:{salida + 0.6 + i * 0.04:.2f}s"/>')

    # Prompt final con el cursor parpadeando.
    fila_fin = filas_arte + 3
    fin = salida + 1.0
    piezas.append(texto(0, fila_fin, [("~ ", ROSA, True), ("$ ", GRIS, False)], fin))
    piezas.append(f'<rect class="cursor" x="{MARGEN + 4 * ANCHO_LETRA:.1f}" '
                  f'y="{MARGEN + fila_fin * ALTO_FILA + 2:.1f}" width="{ANCHO_LETRA:.1f}" '
                  f'height="{ALTO_FILA - 4:.1f}" fill="{ROSA}" style="animation-delay:{fin:.2f}s"/>')

    largo_info = max(sum(len(t) for t, _, _ in linea) for linea in info if linea)
    ancho = round(2 * MARGEN + (col_info + max(largo_info, len(BLOQUES) * 3)) * ANCHO_LETRA)
    alto = round(2 * MARGEN + (fila_fin + 1) * ALTO_FILA)

    estilo = (
        fuente("jbm-Regular.woff2", 400) + fuente("jbm-Bold.woff2", 700) +
        f"text{{font-family:J,'JetBrains Mono',ui-monospace,monospace;font-size:{TAM}px;"
        "white-space:pre;opacity:0;animation:ve 0s steps(1) forwards}"
        ".b{opacity:0;animation:ve 0s steps(1) forwards}"
        ".cursor{opacity:0;animation:parpadea 1.1s steps(1) infinite}"
        "@keyframes ve{to{opacity:1}}"
        "@keyframes parpadea{0%{opacity:1}50%{opacity:0}}"
        ".boot{animation:fuera .2s ease-out forwards}"
        "@keyframes fuera{to{opacity:0}}"
        "@media (prefers-reduced-motion:reduce){text,.b{animation:none;opacity:1}.cursor{animation:none;opacity:1}"
        ".boot{display:none}}"
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{ancho}" height="{alto}" viewBox="0 0 {ancho} {alto}">\n'
        f'<!-- Fuente: JetBrains Mono, SIL Open Font License 1.1 -->\n'
        f'<style>{estilo}</style>\n'
        f'<defs><linearGradient id="borde" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="#b0566f"/><stop offset="1" stop-color="#4f3852"/></linearGradient></defs>\n'
        f'<rect x="1" y="1" width="{ancho - 2}" height="{alto - 2}" rx="10" fill="{FONDO}" '
        f'stroke="url(#borde)" stroke-width="2"/>\n'
        + "\n".join(piezas) + "\n</svg>\n"
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("usuario")
    p.add_argument("--arte", default=str(AQUI / "arte-avatar-vino.json"))
    p.add_argument("--kernel", default="Linux 7.2.14-arch1-1")
    p.add_argument("--datos", help="JSON con los datos ya bajados (para probar sin la API)")
    p.add_argument("--guardar-datos", help="guarda en este JSON los datos bajados de la API")
    p.add_argument("-o", "--salida", default="neofetch.svg")
    a = p.parse_args()

    if a.datos:
        d = json.loads(Path(a.datos).read_text())
    else:
        token = os.environ.get("GH_TOKEN")
        if not token:
            raise SystemExit("Falta GH_TOKEN")
        d = datos_github(a.usuario, token)
        if a.guardar_datos:
            Path(a.guardar_datos).write_text(json.dumps(d, indent=2))
    arte = json.loads(Path(a.arte).read_text())
    Path(a.salida).write_text(construir(a.usuario, a.kernel, arte, d), encoding="utf-8")
    print(f"{a.salida}: {d}")


if __name__ == "__main__":
    main()
