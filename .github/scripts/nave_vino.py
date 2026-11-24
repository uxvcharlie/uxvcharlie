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


if __name__ == "__main__":
    RenderContext.darkmode = _contexto_vino(_tema_desde_argv())
    sys.exit(app())
