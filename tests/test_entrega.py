# tests/test_entrega.py
from clasificador_video.entrega import EstadoEntrega


def test_sin_entrega_previa_es_none():
    assert EstadoEntrega.de_dict(None) is None


def test_ida_y_vuelta_por_dict():
    original = EstadoEntrega(
        estado="con_editor",
        subido_en="2026-09-16T10:00:00",
        prproj_local="/x/Casa Reforma.prproj",
        drive_folder_id="abc123",
        drive_prproj_modificado_en="2026-09-16T10:00:00",
    )

    de_vuelta = EstadoEntrega.de_dict(original.to_dict())

    assert de_vuelta == original


def test_estados_posibles():
    assert EstadoEntrega.SIN_SUBIR == "sin_subir"
    assert EstadoEntrega.CON_EDITOR == "con_editor"
    assert EstadoEntrega.EDITOR_CONTESTO == "editor_contesto"
