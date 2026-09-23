"""La carpeta de proxies que elige Bruno (spec 2026-08-25).

Lo que se prueba aquí es el lado de la ventana: que la elección se use, que
se guarde, y que la pregunta salga UNA sola vez. Las reglas de carpeta viven
en `tests/test_proxy_gen.py`.
"""
from pathlib import Path

import pytest
from PySide6.QtWidgets import QMessageBox

from clasificador_video import proxy_gen
from clasificador_video.manifest import Clip
from clasificador_video.rooms import RoomSelection
from clasificador_video.ui.main_window import MainWindow


class FakeMpv:
    def __init__(self, **kwargs):
        self.pause = True
        self.time_pos = 0.0

    def play(self, path):
        pass

    def command(self, *args):
        pass


@pytest.fixture
def ventana(qtbot):
    seleccion = RoomSelection()
    seleccion.add("Sala")
    w = MainWindow(project_name="Casa Jardín", room_selection=seleccion,
                   video_factory=FakeMpv)
    qtbot.addWidget(w)
    return w


def _con_un_bin(ventana, tmp_path, nombre="02. VIDEO DRONE"):
    material = tmp_path / nombre
    material.mkdir()
    clip = material / "DJI_0001.MP4"
    clip.touch()
    ventana.load_clips([Clip(orden=1, ruta=clip, categoria_path=[], fps=30.0)])
    ventana.bins.agregar(nombre, material, [0])
    return material


def test_la_ventana_arranca_sin_carpeta_elegida(ventana):
    """Nadie contestó todavía: se comporta como siempre."""
    assert ventana.carpeta_de_proxies is None


def test_la_ventana_arranca_sin_carpeta_de_icloud(ventana):
    assert ventana.carpeta_de_icloud is None


def test_set_carpeta_de_icloud_la_guarda(ventana, tmp_path):
    carpeta = tmp_path / "IAV-2609.10-A"

    ventana.set_carpeta_de_icloud(carpeta)

    assert ventana.carpeta_de_icloud == carpeta


def test_la_carpeta_de_icloud_viaja_con_el_proyecto(ventana, tmp_path):
    carpeta = tmp_path / "IAV-2609.10-A"
    ventana.set_carpeta_de_icloud(carpeta)

    data = ventana._datos_del_proyecto()

    assert data["carpeta_de_icloud"] == str(carpeta)


def test_los_proxies_nuevos_van_a_la_subcarpeta_de_la_elegida(ventana, tmp_path):
    material = _con_un_bin(ventana, tmp_path)
    elegida = tmp_path / "07. PROXIES"
    elegida.mkdir()
    ventana.set_carpeta_de_proxies(elegida)

    carpeta, _ya, _pendientes = ventana._repartir_proxies_del_bin("02. VIDEO DRONE")

    assert carpeta == elegida / "02. VIDEO DRONE"


def test_sin_elegir_nada_los_proxies_van_donde_iban(ventana, tmp_path):
    """El guardia de que esto no le cambia el sitio a nadie por su cuenta."""
    material = _con_un_bin(ventana, tmp_path)

    carpeta, _ya, _pendientes = ventana._repartir_proxies_del_bin("02. VIDEO DRONE")

    assert carpeta == proxy_gen.carpeta_de_proxies(material)


def test_un_proxy_de_antes_se_sigue_encontrando_con_carpeta_elegida(
        ventana, tmp_path):
    """Elegir carpeta no invalida lo que ya existe: Bruno pidió explícitamente
    que a los proyectos que ya tiene no se les mueva un solo archivo."""
    material = _con_un_bin(ventana, tmp_path)
    adentro = proxy_gen.carpeta_de_proxies(material)
    adentro.mkdir(parents=True)
    viejo = proxy_gen.ruta_de_proxy(ventana.clips[0].ruta, adentro)
    viejo.touch()
    ventana.set_carpeta_de_proxies(tmp_path / "07. PROXIES")

    _carpeta, ya_en_disco, pendientes = ventana._repartir_proxies_del_bin(
        "02. VIDEO DRONE")

    assert ya_en_disco == [(0, viejo)]
    assert pendientes == []


def test_la_pregunta_sale_una_sola_vez(ventana, tmp_path, monkeypatch):
    """La primera vez que se generan proxies, y nunca más en ese proyecto."""
    _con_un_bin(ventana, tmp_path)
    (tmp_path / "07. PROXIES").mkdir()
    veces = []

    def espia(propuesta):
        veces.append(propuesta)
        return propuesta

    monkeypatch.setattr(ventana, "_preguntar_por_la_carpeta_de_proxies", espia)
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.No))

    ventana.generar_proxies_de_bin("02. VIDEO DRONE")
    ventana.generar_proxies_de_bin("02. VIDEO DRONE")

    assert veces == [tmp_path / "07. PROXIES"], (
        "se pregunta una vez, con la carpeta que Bruno ya tenía como propuesta"
    )
    assert ventana.carpeta_de_proxies == tmp_path / "07. PROXIES"


def test_la_carpeta_elegida_viaja_al_archivo_del_proyecto(ventana, tmp_path):
    elegida = tmp_path / "07. PROXIES"
    elegida.mkdir()
    ventana.set_carpeta_de_proxies(elegida)

    assert ventana._datos_del_proyecto()["carpeta_de_proxies"] == str(elegida)


def test_el_menu_del_bin_deja_cambiar_la_carpeta(ventana, tmp_path):
    """Escoger mal no puede quedar amarrado para siempre."""
    _con_un_bin(ventana, tmp_path)
    ventana._refresh_sheet(force_rebuild=True)
    cabecera = ventana.clip_sheet.bin_header_widget("02. VIDEO DRONE")

    # el menu se sostiene en una variable: sin dueño, Python lo suelta y
    # sus QAction mueren en C++ antes de poder leerlas
    menu = cabecera.construir_menu()
    renglones = [a.text() for a in menu.actions()]

    assert "Cambiar carpeta de proxies…" in renglones


def test_con_carpeta_de_icloud_la_propuesta_de_proxies_va_ahi(
        ventana, tmp_path, monkeypatch):
    _con_un_bin(ventana, tmp_path)
    (tmp_path / "07. PROXIES").mkdir()
    carpeta_proyecto = tmp_path / "IAV-2609.10-A"
    ventana.set_carpeta_de_icloud(carpeta_proyecto)
    propuestas = []

    def espia(propuesta):
        propuestas.append(propuesta)
        return propuesta

    monkeypatch.setattr(ventana, "_preguntar_por_la_carpeta_de_proxies", espia)

    ventana.generar_proxies_de_bin("02. VIDEO DRONE")

    assert propuestas == [carpeta_proyecto / "03. Proxies"]
