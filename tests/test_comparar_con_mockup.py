"""Tests del arnés de comparación (Candado 2 del plan de rediseño).

Solo se prueba la parte pura: los renders necesitan Chrome y una pantalla,
y se verifican mirando la imagen, que es justamente el punto del arnés.
"""
import importlib.util
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "comparar_con_mockup", RAIZ / "scripts" / "comparar_con_mockup.py"
)
comparar = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(comparar)

HTML_MINIMO = "<html><head><title>x</title></head><body></body></html>"


def test_la_inyeccion_deja_visible_solo_la_pantalla_pedida():
    html = comparar.html_aislado(HTML_MINIMO, 0)
    assert ".window.__solo" in html
    assert "querySelectorAll('.window')[0]" in html


def test_la_inyeccion_puede_pedir_la_segunda_pantalla():
    assert "[1]" in comparar.html_aislado(HTML_MINIMO, 1)


def test_la_inyeccion_no_toca_el_cuerpo_del_documento():
    """Se inyecta en <head>: el mockup original nunca se modifica y la
    copia tiene que seguir siendo el mismo documento."""
    html = comparar.html_aislado(HTML_MINIMO, 0)
    assert html.count("<body>") == 1
    assert html.index("__solo") < html.index("</head>")


def test_la_inyeccion_esconde_los_encabezados_y_el_relleno():
    html = comparar.html_aislado(HTML_MINIMO, 0)
    assert ".caption{display:none!important}" in html.replace(" ", "")


def test_el_mockup_de_verdad_admite_la_inyeccion():
    """El reemplazo es sobre '</head>': si el mockup dejara de tenerlo, o
    tuviera dos, el arnés capturaría cualquier cosa en silencio."""
    html = comparar.MOCKUP.read_text(encoding="utf-8")
    assert html.count("</head>") == 1
    assert html.count('class="window"') == 2  # modo clip y modo hoja
    assert "__solo" in comparar.html_aislado(html, 0)


def test_geometria_del_lienzo_es_la_suma_mas_la_separacion():
    ancho, alto = comparar.geometria_lienzo((1600, 1000), (1600, 1000), separacion=40)
    assert ancho == 1600 + 40 + 1600
    assert alto == 1000


def test_geometria_del_lienzo_usa_el_alto_mayor():
    _, alto = comparar.geometria_lienzo((100, 200), (100, 500), separacion=10)
    assert alto == 500
