"""Faro del README: la luz gira solo si hiciste un push público en las últimas 24 horas.

Lee los eventos públicos del usuario (PushEvent). Con luz apagada muestra hace cuánto fue el último.
Solo usa la librería estándar.

Uso:
    GH_TOKEN=... python faro.py uxvcharlie -o faro.svg
    python faro.py uxvcharlie --forzar encendido -o faro.svg    # para probar el diseño sin la API
"""

import argparse
import base64
import json
import os
import random
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

FUENTES = Path(__file__).parent.parent / "fuentes"

ANCHO, ALTO = 840, 300
TAM = 14
LETRA = TAM * 0.6
MARGEN = 24
CX, LAMPARA = 640, 82  # eje del faro y altura de la lámpara

FONDO = "#0d1117"
GRIS = "#8b949e"
TEXTO = "#e6edf3"
CLAVE = "#d87492"
ROSA = "#f0a8bc"
VINO = "#7a2e48"
HORAS_ENCENDIDO = 24


def ultimo_push(usuario: str, token: str | None) -> datetime | None:
    cabeceras = {"User-Agent": "faro-perfil", "Accept": "application/vnd.github+json"}
    if token:
        cabeceras["Authorization"] = f"Bearer {token}"
    pedido = urllib.request.Request(f"https://api.github.com/users/{usuario}/events/public?per_page=100", headers=cabeceras)
    with urllib.request.urlopen(pedido, timeout=30) as r:
        eventos = json.load(r)
    fechas = [e["created_at"] for e in eventos if e["type"] == "PushEvent"]
    return datetime.fromisoformat(max(fechas).replace("Z", "+00:00")) if fechas else None


def hace(cuando: datetime | None) -> str:
    if cuando is None:
        return "hace más de 90 días"
    horas = int((datetime.now(timezone.utc) - cuando).total_seconds() // 3600)
    if horas < 1:
        return "hace menos de una hora"
    if horas < 48:
        return f"hace {horas} h"
    return f"hace {horas // 24} días"


def fuente(nombre: str, peso: int) -> str:
    datos = base64.b64encode((FUENTES / nombre).read_bytes()).decode()
    return (f"@font-face{{font-family:J;font-weight:{peso};"
            f"src:url(data:font/woff2;base64,{datos}) format('woff2')}}")


def faro(encendido: bool, cuando: datetime | None) -> str:
    piezas = []
    azar = random.Random("faro")
    for i in range(70):  # estrellas
        piezas.append(f'<circle cx="{azar.uniform(10, ANCHO - 10):.1f}" cy="{azar.uniform(10, 190):.1f}" '
                      f'r="{azar.choice([0.6, 0.9, 1.2])}" fill="#c9a9b8" opacity="{azar.uniform(0.2, 0.6):.2f}"'
                      f'{f" class=\"t{i % 3}\"" if i % 4 == 0 else ""}/>')

    if encendido:  # haces de luz: dos, uno a cada lado, que se aplastan y se invierten como si el foco girara
        for lado, vuelta in ((1, "a"), (-1, "b")):
            fin = CX + lado * 560
            piezas.append(f'<polygon points="{CX},{LAMPARA - 5} {fin},{LAMPARA - 70} {fin},{LAMPARA + 60}" '
                          f'fill="url(#haz{"R" if lado == 1 else "L"})" class="haz {vuelta}"/>')
        piezas.append(f'<circle cx="{CX}" cy="{LAMPARA}" r="42" fill="url(#halo)" class="pulso"/>')

    # Mar: dos olas desfasadas.
    for k, (y, color, dur) in enumerate(((236, "#2a1620", 7), (252, "#4a1c2d", 5))):
        trazo = "M-40," + str(y) + " " + " ".join(f"q40,-12 80,0 t80,0" for _ in range(12)) + f" V{ALTO} H-40 Z"
        piezas.append(f'<path d="{trazo}" fill="{color}" class="ola" style="animation-duration:{dur}s"/>')

    # Roca y torre: franjas rosa y vino.
    piezas.append(f'<path d="M{CX - 85},{ALTO} Q{CX - 60},218 {CX - 30},206 L{CX + 30},206 Q{CX + 62},218 {CX + 90},{ALTO}Z" fill="#1a0f15"/>')
    base_y, alto_torre = 206, 106
    for i in range(4):
        y0 = base_y - alto_torre + i * alto_torre / 4
        y1 = y0 + alto_torre / 4
        a0 = 15 + (y0 - (base_y - alto_torre)) / alto_torre * 12
        a1 = 15 + (y1 - (base_y - alto_torre)) / alto_torre * 12
        piezas.append(f'<polygon points="{CX - a0:.1f},{y0:.1f} {CX + a0:.1f},{y0:.1f} {CX + a1:.1f},{y1:.1f} {CX - a1:.1f},{y1:.1f}" '
                      f'fill="{ROSA if i % 2 == 0 else VINO}"/>')
    piezas.append(f'<rect x="{CX - 22}" y="{LAMPARA + 13}" width="44" height="6" fill="#4a1c2d"/>')           # balcón
    piezas.append(f'<rect x="{CX - 13}" y="{LAMPARA - 12}" width="26" height="25" fill="{"#fff1f5" if encendido else "#1a0f15"}" '
                  f'stroke="#4a1c2d" stroke-width="2"/>')                                                      # lámpara
    piezas.append(f'<polygon points="{CX - 17},{LAMPARA - 12} {CX},{LAMPARA - 30} {CX + 17},{LAMPARA - 12}" fill="{VINO}"/>')
    piezas.append(f'<rect x="{CX - 4}" y="{206 - 22}" width="8" height="22" rx="4" fill="#0d1117"/>')        # puerta

    # Estado, como systemctl.
    punto, estado, color = ("●", "active (running)", "#d87492") if encendido else ("○", "inactive (dead)", GRIS)
    lineas = [
        f'<tspan fill="{CLAVE}">uxvcharlie@arch</tspan><tspan fill="{GRIS}">:~$</tspan><tspan fill="{TEXTO}" dx="{LETRA:.1f}">systemctl status faro</tspan>',
        f'<tspan fill="{color}">{punto}</tspan><tspan fill="{TEXTO}" dx="{LETRA:.1f}">faro.service</tspan><tspan fill="{GRIS}" dx="{LETRA:.1f}">- luz de commits</tspan>',
        f'<tspan fill="{GRIS}">Estado:</tspan><tspan fill="{color}" dx="{LETRA:.1f}">{estado}</tspan>',
        f'<tspan fill="{GRIS}">Último push:</tspan><tspan fill="{TEXTO}" dx="{LETRA:.1f}">{escape(hace(cuando))}</tspan>',
        f'<tspan fill="{GRIS}">Regla:</tspan><tspan fill="{TEXTO}" dx="{LETRA:.1f}">se enciende con un push en las últimas {HORAS_ENCENDIDO} h</tspan>',
    ]
    for i, t in enumerate(lineas):
        piezas.append(f'<text x="{MARGEN}" y="{MARGEN + 14 + i * 24 + (10 if i else 0)}" font-size="{TAM}">{t}</text>')

    estilo = (fuente("jbm-latin-Regular.woff2", 400) + fuente("jbm-latin-Bold.woff2", 700) +
              "text{font-family:J,'JetBrains Mono',ui-monospace,monospace;white-space:pre}"
              "@keyframes t{0%,100%{opacity:.15}50%{opacity:.8}}"
              ".t0{animation:t 4s ease-in-out infinite}.t1{animation:t 6s ease-in-out -2s infinite}.t2{animation:t 5s ease-in-out -4s infinite}"
              f"@keyframes giro{{0%{{transform:scaleX(1)}}50%{{transform:scaleX(-1)}}100%{{transform:scaleX(1)}}}}"
              f".haz{{transform-origin:{CX}px {LAMPARA}px;animation:giro 6s ease-in-out infinite}}.haz.b{{animation-delay:-3s}}"
              "@keyframes pulso{0%,100%{opacity:.55}50%{opacity:1}}.pulso{animation:pulso 3s ease-in-out infinite}"
              "@keyframes ola{0%{transform:translateX(0)}100%{transform:translateX(-80px)}}.ola{animation:ola linear infinite}")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{ANCHO}" height="{ALTO}" viewBox="0 0 {ANCHO} {ALTO}">\n'
        f'<!-- Fuente: JetBrains Mono, SIL Open Font License 1.1 -->\n'
        f'<title>Faro: {"encendido" if encendido else "apagado"}</title>\n<style>{estilo}</style>\n'
        f'<defs><linearGradient id="borde" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#b0566f"/>'
        f'<stop offset="1" stop-color="#4f3852"/></linearGradient>'
        f'<clipPath id="marco"><rect x="1" y="1" width="{ANCHO - 2}" height="{ALTO - 2}" rx="10"/></clipPath>'
        f'<linearGradient id="hazR" x1="0" x2="1"><stop offset="0" stop-color="#ffe3ec" stop-opacity="0.75"/>'
        f'<stop offset="1" stop-color="#d87492" stop-opacity="0"/></linearGradient>'
        f'<linearGradient id="hazL" x1="1" x2="0"><stop offset="0" stop-color="#ffe3ec" stop-opacity="0.75"/>'
        f'<stop offset="1" stop-color="#d87492" stop-opacity="0"/></linearGradient>'
        f'<radialGradient id="halo"><stop offset="0" stop-color="#ffe3ec" stop-opacity="0.9"/>'
        f'<stop offset="1" stop-color="#d87492" stop-opacity="0"/></radialGradient></defs>\n'
        f'<rect x="1" y="1" width="{ANCHO - 2}" height="{ALTO - 2}" rx="10" fill="{FONDO}"/>\n'
        f'<g clip-path="url(#marco)">\n' + "\n".join(piezas) + '\n</g>\n'
        f'<rect x="1" y="1" width="{ANCHO - 2}" height="{ALTO - 2}" rx="10" fill="none" stroke="url(#borde)" stroke-width="1.5"/>\n</svg>\n')


def main():
    p = argparse.ArgumentParser()
    p.add_argument("usuario")
    p.add_argument("-o", "--salida", default="faro.svg")
    p.add_argument("--forzar", choices=["encendido", "apagado"], help="probar el diseño sin pedir nada a la API")
    a = p.parse_args()
    if a.forzar:
        cuando = datetime.now(timezone.utc) if a.forzar == "encendido" else datetime(2026, 11, 17, tzinfo=timezone.utc)
        encendido = a.forzar == "encendido"
    else:
        cuando = ultimo_push(a.usuario, os.environ.get("GH_TOKEN"))
        encendido = cuando is not None and (datetime.now(timezone.utc) - cuando).total_seconds() < HORAS_ENCENDIDO * 3600
    Path(a.salida).write_text(faro(encendido, cuando), encoding="utf-8")
    print("encendido" if encendido else "apagado", hace(cuando))


if __name__ == "__main__":
    main()
