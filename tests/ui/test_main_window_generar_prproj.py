"""Ctrl+E genera el proyecto de Premiere directamente."""
from pathlib import Path
from unittest.mock import patch

import pytest
from PySide6.QtCore import Qt

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
def ventana_con_clips(qtbot, tmp_path):
    ventana = MainWindow(project_name="IAV-2609.10-A",
                         room_selection=RoomSelection(), video_factory=FakeMpv)
    qtbot.addWidget(ventana)
    archivo = tmp_path / "C0001.MP4"
    archivo.write_bytes(b"")
    ventana.load_clips([
        Clip(orden=1, ruta=archivo, categoria_path=["Cocina"], fps=59.94)])
    return ventana


def test_ctrl_e_llama_a_generar_prproj(
        ventana_con_clips, tmp_path, monkeypatch):
    destino = tmp_path / "IAV-2609.10-A.prproj"
    monkeypatch.setattr(ventana_con_clips, "_ruta_sugerida_del_prproj",
                        lambda: str(destino))
    monkeypatch.setattr(ventana_con_clips, "_avisar_prproj_generado",
                        lambda _destino: None)
    with patch("clasificador_video.ui.main_window.prproj_generador.generar_prproj") as generar:
        ventana_con_clips._on_generar_prproj()
    generar.assert_called_once()


def test_exportar_solo_ofrece_el_prproj(ventana_con_clips):
    boton = ventana_con_clips.title_bar.export_button
    assert boton.contextMenuPolicy() == Qt.ContextMenuPolicy.DefaultContextMenu
    assert "plugin" not in boton.toolTip().lower()
    assert not hasattr(ventana_con_clips.title_bar, "export_manifest_requested")


def test_si_el_prproj_ya_existe_genera_la_siguiente_version(
        ventana_con_clips, tmp_path, monkeypatch):
    destino = tmp_path / "IAV-2609.10-A.prproj"
    destino.write_bytes(b"trabajo de ayer")
    monkeypatch.setattr(ventana_con_clips, "_ruta_sugerida_del_prproj",
                        lambda: str(destino))
    avisos = []
    monkeypatch.setattr(ventana_con_clips, "_avisar_prproj_generado",
                        lambda ruta: avisos.append(ruta))
    with patch("clasificador_video.ui.main_window.prproj_generador.generar_prproj") as generar:
        ventana_con_clips._on_generar_prproj()
    generar.assert_called_once()
    assert generar.call_args.args[1] == tmp_path / "IAV-2609.10-A v2.prproj"
    assert avisos == [tmp_path / "IAV-2609.10-A v2.prproj"]
    assert destino.read_bytes() == b"trabajo de ayer"
