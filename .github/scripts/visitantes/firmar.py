"""Registra una firma en el muro de visitantes: baja el avatar de quien firmó, lo pasa a ASCII
con imagen-a-ascii y lo guarda en firmas.json (una entrada por persona; si firma otra vez, se actualiza).

En el Action lee el issue del evento (GITHUB_EVENT_PATH). Para probar a mano: --usuario LOGIN.
Solo se guarda el nombre de usuario de GitHub, la fecha y el arte: ningún texto que escriba la persona.

Uso:
    python firmar.py firmas.json                 # desde el Action, con el issue del evento
    python firmar.py firmas.json --usuario octocat
"""

import argparse
import json
import os
import re
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from imagen_a_ascii import nucleo

COLUMNAS = 22
# El muro usa interlineado 1.2: menos filas que en la herramienta para que la cara no salga estirada.
nucleo.ASPECTO = 0.6 / 1.2


def cuantizar(color: str) -> str:
    """Redondea a pasos de 16 para que tramos vecinos casi iguales se junten (SVG más liviano)."""
    return "".join(f"{min(255, round(int(color[i:i + 2], 16) / 16) * 16):02x}" for i in (0, 2, 4))


def a_tramos(filas):
    salida = []
    for fila in filas:
        tramos = []
        for letra, color in fila:
            color = None if letra == " " else cuantizar(color)
            if tramos and tramos[-1][1] == color:
                tramos[-1][0] += letra
            else:
                tramos.append([letra, color])
        salida.append(tramos)
    return salida


# Todo el muro en la escala vino, según qué tan llena es cada letra: así queda parejo
# aunque cada avatar tenga sus propios colores.
VINO = ["7a2e48", "7a2e48", "7a2e48", "b0566f", "b0566f", "d87492", "d87492", "f0a8bc", "f0a8bc", "f0a8bc"]


def por_valor(filas, rampa: str, curva: float):
    """Letra según el canal más fuerte del color, no la luminancia: un rojo oscuro
    (como el murciélago de un avatar) pesa 0.21 en luminancia y saldría casi vacío."""
    base = 18 / 255  # imagen-a-ascii suma 18 a cada canal sobre fondo oscuro
    n = len(rampa)
    salida = []
    for fila in filas:
        nueva = []
        for _, color in fila:
            v = max(int(color[i:i + 2], 16) for i in (0, 2, 4)) / 255
            v = max(0.0, (v - base) / (1 - base))
            nueva.append((rampa[min(n - 1, int(v ** curva * n))], color))
        salida.append(nueva)
    return salida


def en_vino(filas, rampa: str):
    return [[(letra, VINO[rampa.index(letra)]) for letra, _ in fila] for fila in filas]


def arte_de(usuario: str, url_avatar: str) -> list:
    pedido = urllib.request.Request(url_avatar, headers={"User-Agent": "muro-visitantes"})
    with urllib.request.urlopen(pedido, timeout=30) as r, \
            tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(r.read())
        ruta = f.name
    try:
        # Avatar de fondo claro (octocat, identicons): se invierte para que el fondo quede vacío
        # y la figura lleve la tinta, como en uno de fondo oscuro.
        claro = nucleo.es_clara(ruta)
        aj = nucleo.Ajustes(columnas=COLUMNAS, rampa=nucleo.RAMPAS["simple"], curva=1.0, brillo=125,
                            claro=claro, fondo="#f6f1e7" if claro else "#0d1117")
        filas = nucleo.a_celdas(nucleo.abrir(ruta, aj), aj)
        if not claro:
            filas = por_valor(filas, aj.rampa, 1.3)
        return a_tramos(en_vino(filas, aj.rampa))
    finally:
        os.unlink(ruta)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("firmas")
    p.add_argument("--usuario", help="firmar a mano con este usuario (para probar)")
    a = p.parse_args()

    if a.usuario:
        usuario = a.usuario
        fecha = datetime.now(timezone.utc).isoformat(timespec="seconds")
    else:
        evento = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
        usuario = evento["issue"]["user"]["login"]
        fecha = evento["issue"]["created_at"]
    # Los nombres de GitHub solo llevan letras, números y guiones (y [bot] en las apps).
    if not re.fullmatch(r"[A-Za-z0-9-]{1,39}(\[bot\])?", usuario):
        raise SystemExit(f"Usuario raro, no se firma: {usuario!r}")

    url = f"https://github.com/{usuario}.png?size=96"
    entrada = {"usuario": usuario, "fecha": fecha, "arte": arte_de(usuario, url)}

    ruta = Path(a.firmas)
    firmas = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else []
    firmas = [f for f in firmas if f["usuario"].lower() != usuario.lower()] + [entrada]
    firmas.sort(key=lambda f: f["fecha"])
    ruta.write_text(json.dumps(firmas, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"firmó {usuario} ({len(firmas)} firmas)")


if __name__ == "__main__":
    main()
