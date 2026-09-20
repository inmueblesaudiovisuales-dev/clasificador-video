# tests/ui/test_clip_sheet_unidades.py
"""Agrupar por unidad, arriba de cuarto. Sin ninguna unidad en el
proyecto, el agrupamiento es el de siempre -- sin este nivel extra."""
from pathlib import Path

import pytest

from clasificador_video.ui.clip_sheet import ClipSheet, ClipThumbnail, SIN_UNIDAD


def _thumb(unidad, cuarto, bin_nombre="Sony"):
    return ClipThumbnail(
        path=Path("/tmp/x.mp4"), room_label=cuarto, flag="none",
        room_color=None, numero=1, in_frame=None, out_frame=None,
        fps=30.0, duration_frames=None, aspect_ratio=16 / 9,
        bin_nombre=bin_nombre, tiene_proxy=False, unit_label=unidad,
    )


@pytest.fixture
def hoja(qtbot):
    h = ClipSheet()
    qtbot.addWidget(h)
    return h


def test_sin_unidades_en_el_proyecto_no_agrupa_por_unidad(hoja):
    hoja.set_clips([_thumb(None, "Cocina")])
    assert hoja._group_of(hoja.item_widgets[0].clip) == ("Sony", None, "Cocina")


def test_con_unidad_el_grupo_incluye_la_unidad(hoja):
    # El proyecto declara sus unidades con `set_unit_order`, igual que
    # declara sus cuartos con `set_room_order` -- sin eso, `_hay_unidades`
    # se queda en `False` y este clip no tendria como saber que "Casa A"
    # es una unidad de verdad y no un dato suelto de una migracion vieja.
    hoja.set_unit_order(["Casa A"])
    hoja.set_clips([_thumb("Casa A", "Cocina")])
    assert hoja._group_of(hoja.item_widgets[0].clip) == ("Sony", "Casa A", "Cocina")


def test_clip_sin_unidad_cae_en_sin_unidad_si_el_proyecto_tiene_unidades(hoja):
    hoja.set_unit_order(["Casa A"])
    hoja.set_clips([_thumb(None, "Cocina")])
    assert hoja._group_of(hoja.item_widgets[0].clip) == ("Sony", SIN_UNIDAD, "Cocina")


def test_proyecto_sin_unidades_agrupa_exactamente_como_antes(hoja):
    hoja.set_clips([_thumb(None, "Cocina"), _thumb(None, "Baño")])
    grupos = {hoja._group_of(w.clip) for w in hoja.item_widgets}
    assert grupos == {("Sony", None, "Cocina"), ("Sony", None, "Baño")}
