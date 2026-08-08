import inspect
import re
from pathlib import Path

from clasificador_video.ui import theme
from clasificador_video.ui.theme import (
    BG_APP,
    BG_SURFACE_0,
    CURRENT_COLOR,
    build_stylesheet,
)


def test_build_stylesheet_incluye_el_fondo_oscuro_de_la_ventana():
    qss = build_stylesheet()
    assert f"background-color: {BG_APP}" in qss


def test_build_stylesheet_estiliza_los_paneles():
    qss = build_stylesheet()
    assert f"background-color: {BG_SURFACE_0}" in qss


def test_build_stylesheet_da_estilo_al_boton_principal():
    qss = build_stylesheet()
    assert "QPushButton#startButton" in qss
    assert "QPushButton#exportButton" in qss
    assert CURRENT_COLOR in qss


def test_build_stylesheet_da_fondo_negro_al_video():
    qss = build_stylesheet()
    assert "QWidget#videoWidget" in qss
    assert "background-color: black" in qss


def test_build_stylesheet_da_fondo_distinto_al_boton_importar():
    """Bug real de v1: el boton 'Importar carpetas...' usaba el mismo
    color de fondo que el panel donde vive y era invisible como boton.
    """
    qss = build_stylesheet()
    assert "QPushButton#importButton" in qss


def test_build_stylesheet_es_una_sola_cadena_no_vacia():
    qss = build_stylesheet()
    assert isinstance(qss, str)
    assert len(qss) > 100


# ---------------------------------------------------------------------------
# Tokens de diseño (F1 del rediseño). Los valores salen del bloque `:root` de
# docs/superpowers/mockups/rediseno-2026-08-08/mockup.html -- son la
# definicion operativa de "igual al mockup".
# ---------------------------------------------------------------------------


def test_tokens_de_superficie_son_los_del_mockup():
    assert theme.BG_APP == "#0a0b0d"
    assert theme.BG_SURFACE_0 == "#101216"
    assert theme.BG_SURFACE_1 == "#16191e"
    assert theme.BG_SURFACE_2 == "#1d2128"
    assert theme.LINE == "#262b33"
    assert theme.LINE_SOFT == "#1e222a"


def test_tokens_de_texto_son_los_del_mockup():
    assert theme.TEXT == "#e6e9ee"
    assert theme.TEXT_2 == "#9aa3b0"
    assert theme.TEXT_3 == "#626b78"


def test_tokens_de_estado_son_los_del_mockup():
    assert theme.PICK_COLOR == "#55c08a"
    assert theme.STAR_COLOR == "#7ee6b0"
    assert theme.REJECT_COLOR == "#d4696c"
    assert theme.CURRENT_COLOR == "#e8a33d"
    assert theme.TRIM_COLOR == "#6d8cf5"


def test_paleta_de_cuartos_tiene_nueve_colores_del_mockup():
    assert theme.ROOM_PALETTE == [
        "#c0885a", "#6d8ca8", "#8b7ca8", "#4f9a8e", "#7e9e5e",
        "#3e9bc0", "#a9836f", "#b26f86", "#7c8794",
    ]


def test_room_color_es_estable_y_da_la_vuelta():
    assert theme.room_color(0) == "#c0885a"
    assert theme.room_color(9) == theme.room_color(0)


def test_la_barra_de_rango_va_semitransparente_sobre_la_miniatura():
    """Un color solido ahi se ve como una banda opaca tapando la imagen: la
    barra de rango se pinta ENCIMA del frame, no al lado."""
    assert theme.RANGE_TRACK_RGBA == (255, 255, 255, 26)


def test_los_tokens_de_la_tarjeta_salen_del_mockup():
    assert theme.CARD_BADGE_BG_RGBA == (4, 5, 7, 165)
    assert theme.CARD_BADGE_TEXT == "#e4e8ee"
    assert theme.UNCLASSIFIED_STRIPE == "#3a4150"
    assert theme.SELECTION_BORDER == "#8fb4ff"
    assert theme.SELECTION_TICK_INK == "#0a1024"


def test_las_tintas_de_los_glifos_contrastan_contra_su_color_de_estado():
    """El glifo `P` va en tinta oscura SOBRE el verde de pick, no al reves."""
    assert theme.PICK_INK == "#07130d"
    assert theme.REJECT_INK == "#1b0708"


def test_pendiente_tiene_color_propio_y_no_es_una_superficie():
    """El tramo 'lo que falta' de la barra y el punto gris de la leyenda son
    el mismo dato; el mockup les da un gris propio, no un fondo de panel."""
    assert theme.PENDING_COLOR == "#2a2f38"
    assert theme.PENDING_COLOR != theme.BG_SURFACE_2


def test_mezclar_con_blanco_aclara_sin_cambiar_de_tono():
    """De aqui sale el texto del badge de cuarto sobre el video."""
    assert theme.aclarar("#000000", 0.5) == "#808080"
    assert theme.aclarar("#c0885a", 0.0) == "#c0885a"
    assert theme.aclarar("#c0885a", 1.0) == "#ffffff"


def test_con_alfa_devuelve_el_color_en_forma_de_tupla_para_qpainter():
    """QColor no parsea la notacion CSS: QColor('rgba(...)') es invalido."""
    assert theme.con_alfa("#55c08a", 140) == (85, 192, 138, 140)


def test_los_tokens_que_la_f2_dejo_sin_usar_ya_no_existen():
    """Un token sin destinatario es una funcion perdida esperando. Los dos
    huerfanos de la F2 eran justo los de la barra de rango y el texto 'sin
    marca' de la tarjeta vieja (ver ANALISIS-2026-08-08-post-f2 §2). El
    primero revive con otra forma -- RANGE_TRACK_RGBA, semitransparente --
    y el segundo muere: el mockup no dibuja NADA cuando no hay flag, y esa
    ausencia es la informacion."""
    assert not hasattr(theme, "RANGE_TRACK_COLOR")
    assert not hasattr(theme, "FLAG_NONE_COLOR")


def test_dimensiones_fijas_del_mockup():
    assert theme.TITLEBAR_HEIGHT == 36
    assert theme.STATUSBAR_HEIGHT == 24
    assert theme.RAIL_WIDTH == 200
    assert theme.TOOLCOL_WIDTH == 56
    assert theme.SHEET_MIN_WIDTH == 340


def test_escala_tipografica_es_entera():
    """QSS interpreta mal los tamaños fraccionarios de fuente: se fijan
    enteros para que el resultado sea deterministico."""
    for name in ("FONT_MICRO", "FONT_SMALL", "FONT_BODY", "FONT_TITLE",
                 "FONT_TIMECODE", "FONT_BIG"):
        value = getattr(theme, name)
        assert isinstance(value, int), f"{name} debe ser int, es {type(value)}"


def test_no_quedan_alias_de_compatibilidad():
    """Los alias existieron solo mientras convivieron los widgets viejos
    con la paleta nueva. Dejarlos vivos invita a que alguien vuelva a
    escribir BG_WINDOW en vez de BG_APP y se pierda el sentido de los
    cuatro niveles de superficie."""
    for name in ("BG_WINDOW", "BG_PANEL", "BG_RAIL", "BG_HOVER", "BG_ACTIVE",
                 "TEXT_MUTED", "BORDER", "ACCENT"):
        assert not hasattr(theme, name), f"el alias {name} sigue vivo"


def test_apply_letter_spacing_cambia_la_fuente_del_widget(qtbot):
    """QSS no tiene `letter-spacing`: el tracking de las etiquetas en
    mayusculas solo se puede aplicar por QFont desde codigo."""
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QLabel

    label = QLabel("CUARTOS")
    qtbot.addWidget(label)
    theme.apply_letter_spacing(label, 2.0)
    assert label.font().letterSpacingType() == QFont.SpacingType.AbsoluteSpacing
    assert label.font().letterSpacing() == 2.0


# ---------------------------------------------------------------------------
# Candado 1 del plan de rediseño: theme.py es la UNICA fuente de color.
# ---------------------------------------------------------------------------


def test_build_stylesheet_no_tiene_colores_escritos_a_mano():
    """Todo valor visual sale de un token. Un hexadecimal literal dentro
    de la hoja de estilos es exactamente como empieza la deriva contra el
    mockup."""
    fuente = inspect.getsource(theme.build_stylesheet)
    literales = re.findall(r"#[0-9a-fA-F]{6}\b", fuente)
    assert literales == [], f"colores a mano en build_stylesheet: {literales}"


def test_ningun_modulo_declara_colores_fuera_del_tema():
    """Si un widget puede inventar su propio gris, la app deja de
    parecerse al mockup en el primer commit apurado."""
    raiz = Path(__file__).resolve().parents[2] / "src" / "clasificador_video"
    patron = re.compile(r"#[0-9a-fA-F]{6}\b|rgba?\(")
    ofensores = []
    for archivo in sorted(raiz.rglob("*.py")):
        if archivo.name == "theme.py" or "__pycache__" in archivo.parts:
            continue
        for numero, linea in enumerate(archivo.read_text(encoding="utf-8").splitlines(), 1):
            if patron.search(linea):
                ofensores.append(f"{archivo.relative_to(raiz)}:{numero}: {linea.strip()}")
    assert ofensores == [], "colores fuera de theme.py:\n" + "\n".join(ofensores)
