"""Corre gh-space-shooter con colores vino en vez del verde/azul de GitHub.

No modifica el paquete: reemplaza RenderContext.darkmode() antes de llamar
a la CLI original, así que acepta los mismos argumentos que gh-space-shooter.

Uso:
    python nave_vino.py [--tema hueso|rosa] uxvcharlie -o assets/nave-vino.gif
"""

import sys

from gh_space_shooter.cli import app
from gh_space_shooter.game.render_context import RenderContext

FONDO = (13, 17, 23)        # mismo fondo oscuro de GitHub, para que se funda con la página
CUADRICULA = (33, 22, 29)   # días sin commits: tinta con un toque vino
ENEMIGOS = {                # nivel 1 (pocos commits) a 4 (muchos)
    1: (150, 56, 88),       # contraste 2.7 con el fondo, parecido al verde 1 de GitHub (2.9)
    2: (186, 80, 112),
    3: (216, 116, 146),
    4: (242, 168, 188),
}

TEMAS = {
    # nave clara y balas doradas: contrasta con los enemigos vino
    "hueso": {"ship_color": (232, 222, 214), "bullet_color": (217, 178, 104)},
    # todo dentro de la gama vino/rosa
    "rosa": {"ship_color": (240, 176, 194), "bullet_color": (255, 214, 224)},
}


def _tema_desde_argv() -> str:
    """Saca --tema de sys.argv para que typer no lo vea."""
    tema = "hueso"
    if "--tema" in sys.argv:
        i = sys.argv.index("--tema")
        tema = sys.argv[i + 1]
        del sys.argv[i : i + 2]
    if tema not in TEMAS:
        sys.exit(f"Tema desconocido: {tema}. Opciones: {', '.join(TEMAS)}")
    return tema


def _contexto_vino(tema: str):
    def darkmode() -> RenderContext:
        return RenderContext(
            cell_size=12,
            cell_spacing=3,
            padding=40,
            background_color=FONDO,
            grid_color=CUADRICULA,
            enemy_colors=ENEMIGOS,
            **TEMAS[tema],
        )

    return staticmethod(darkmode)


def _con_marco(render_frame):
    """Dibuja en cada cuadro el borde redondeado vino → ciruela de las demás tarjetas del README."""
    from PIL import Image, ImageDraw

    marco = {}

    def envuelto(self):
        cuadro = render_frame(self)
        if "capa" not in marco:
            ancho, alto = cuadro.size
            # Degradado en diagonal, igual al de neofetch: #b0566f arriba a la izquierda, #4f3852 abajo.
            degradado = Image.new("RGB", (ancho, alto))
            px = degradado.load()
            for y in range(alto):
                for x in range(ancho):
                    t = (x / ancho + y / alto) / 2
                    px[x, y] = tuple(round(a + (b - a) * t) for a, b in zip((176, 86, 111), (79, 56, 82)))
            mascara = Image.new("L", (ancho, alto), 0)
            ImageDraw.Draw(mascara).rounded_rectangle(
                (1, 1, ancho - 2, alto - 2), radius=10, outline=255, width=2)
            # Las esquinas por fuera del redondeo quedan del color del fondo de GitHub.
            esquinas = Image.new("L", (ancho, alto), 255)
            ImageDraw.Draw(esquinas).rounded_rectangle((0, 0, ancho - 1, alto - 1), radius=11, fill=0)
            marco["capa"], marco["mascara"], marco["esquinas"] = degradado, mascara, esquinas
        cuadro.paste(FONDO, mask=marco["esquinas"])
        cuadro.paste(marco["capa"], mask=marco["mascara"])
        return cuadro

    return envuelto


if __name__ == "__main__":
    from gh_space_shooter.game.renderer import Renderer

    RenderContext.darkmode = _contexto_vino(_tema_desde_argv())
    Renderer.render_frame = _con_marco(Renderer.render_frame)
    sys.exit(app())
