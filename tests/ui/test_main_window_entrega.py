from pathlib import Path
import json

import pytest
from PySide6.QtWidgets import QMessageBox

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
    window = MainWindow(project_name="IAV-2609.10-A", room_selection=RoomSelection(),
                        video_factory=FakeMpv)
    qtbot.addWidget(window)
    return window


def test_al_pedir_subir_llama_a_preguntar_con_los_candidatos(ventana, tmp_path, monkeypatch):
    from clasificador_video import preferencias

    raiz = tmp_path / "IAV"
    (raiz / "2026").mkdir(parents=True)
    (raiz / "2026" / f"{ventana.project_name}.prproj").touch()
    monkeypatch.setattr(preferencias, "carpeta_de_proyectos_premiere", lambda: raiz)
    llamado = {}
    monkeypatch.setattr(
        ventana, "_preguntar_por_el_prproj",
        lambda candidatos: (llamado.setdefault("candidatos", candidatos), None)[1],
    )

    ventana._al_pedir_subir_a_drive()

    assert len(llamado["candidatos"]) == 1


def test_confirmar_traer_de_vuelta_sin_cambios_no_bloquea(ventana, monkeypatch):
    from clasificador_video.drive import ResultadoDeRevision

    monkeypatch.setattr(QMessageBox, "exec", lambda self: None)
    monkeypatch.setattr(QMessageBox, "clickedButton", lambda self: self.buttons()[0])
    resultado = ResultadoDeRevision(
        hay_cambios=False, prproj_modificado_en="x", tiene_material_nuevo=False)

    assert ventana._confirmar_traer_de_vuelta(resultado) is True


def test_el_estado_de_entrega_se_guarda_en_el_proyecto(ventana, tmp_path):
    from clasificador_video.entrega import EstadoEntrega

    ventana._entrega = EstadoEntrega(EstadoEntrega.CON_EDITOR, drive_folder_id="carpeta")

    assert ventana._datos_del_proyecto()["entrega"]["drive_folder_id"] == "carpeta"


def test_revisar_cambios_marca_que_el_editor_contesto(ventana, monkeypatch):
    from clasificador_video import drive
    from clasificador_video.drive import ResultadoDeRevision
    from clasificador_video.entrega import EstadoEntrega

    ventana._entrega = EstadoEntrega(EstadoEntrega.CON_EDITOR, drive_folder_id="carpeta")
    ventana._drive_cliente = object()
    monkeypatch.setattr(
        drive, "revisar_cambios",
        lambda *args: ResultadoDeRevision(True, "nuevo", False),
    )
    monkeypatch.setattr(ventana, "_confirmar_traer_de_vuelta", lambda resultado: False)

    ventana._al_pedir_traer_de_vuelta()

    assert ventana._entrega.estado == EstadoEntrega.EDITOR_CONTESTO


def test_refrescar_actualiza_el_cvproj_cuando_hay_cambios(ventana, tmp_path, monkeypatch):
    from clasificador_video.entrega import EstadoEntrega

    ruta = tmp_path / "Casa Reforma.cvproj"
    data = {"entrega": EstadoEntrega(
        estado=EstadoEntrega.CON_EDITOR, drive_folder_id="folder-x",
        drive_prproj_modificado_en="2026-09-16T10:00:00Z",
    ).to_dict()}
    ruta.write_text(json.dumps(data))

    class _ClienteFalso:
        def listar_en_carpeta(self, carpeta_id):
            class _A:
                name = "Casa Reforma.prproj"
                modified_time = "2026-09-18T12:00:00Z"
                mime_type = "video/mp4"
            return [_A()]

    monkeypatch.setattr(ventana, "_cliente_de_drive", lambda: _ClienteFalso())

    ventana._al_refrescar_entrega(ruta)

    guardado = json.loads(ruta.read_text())
    assert guardado["entrega"]["estado"] == EstadoEntrega.EDITOR_CONTESTO
