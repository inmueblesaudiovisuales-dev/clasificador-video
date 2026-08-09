import json
from pathlib import Path

import pytest

from clasificador_video.probe import (
    orientacion_de,
    orientacion_predominante,
    probe_clip,
)

FFPROBE_JSON_CON_AUDIO = json.dumps({
    "streams": [
        {"codec_type": "video", "width": 3840, "height": 2160, "r_frame_rate": "30000/1001"},
        {"codec_type": "audio", "channels": 2},
    ],
    "format": {"duration": "30.03"},
})

FFPROBE_JSON_SIN_AUDIO = json.dumps({
    "streams": [
        {"codec_type": "video", "width": 1920, "height": 1080, "r_frame_rate": "24000/1001"},
    ],
    "format": {"duration": "10.0"},
})


def test_probe_detecta_audio_y_fps_ntsc():
    result = probe_clip(Path("/shooting/C0001.MP4"), runner=lambda path: FFPROBE_JSON_CON_AUDIO)
    assert result["width"] == 3840
    assert result["height"] == 2160
    assert result["has_audio"] is True
    assert abs(result["fps"] - 29.97) < 0.01
    assert result["duration_frames"] == round(30.03 * (30000 / 1001))


def test_probe_sin_audio():
    result = probe_clip(Path("/shooting/DJI_0001.MP4"), runner=lambda path: FFPROBE_JSON_SIN_AUDIO)
    assert result["has_audio"] is False
    assert abs(result["fps"] - 23.976) < 0.01


def test_probe_sin_pista_de_video_lanza_error_claro():
    sin_video = json.dumps({"streams": [], "format": {"duration": "1.0"}})
    with pytest.raises(ValueError, match="no encontro pista de video"):
        probe_clip(Path("/shooting/audio_only.wav"), runner=lambda path: sin_video)


FFPROBE_JSON_VERTICAL_SIDE_DATA = json.dumps({
    "streams": [
        {
            "codec_type": "video",
            "width": 3840,
            "height": 2160,
            "r_frame_rate": "60000/1001",
            "side_data_list": [{"side_data_type": "Display Matrix", "rotation": 90}],
        },
        {"codec_type": "audio", "channels": 2},
    ],
    "format": {"duration": "2.002"},
})

FFPROBE_JSON_VERTICAL_TAG_VIEJO = json.dumps({
    "streams": [
        {
            "codec_type": "video",
            "width": 1920,
            "height": 1080,
            "r_frame_rate": "30/1",
            "tags": {"rotate": "270"},
        },
    ],
    "format": {"duration": "5.0"},
})

FFPROBE_JSON_HORIZONTAL_SIN_ROTACION = json.dumps({
    "streams": [
        {"codec_type": "video", "width": 1920, "height": 1080, "r_frame_rate": "25/1"},
    ],
    "format": {"duration": "5.0"},
})


def test_probe_clip_vertical_intercambia_width_height_por_rotacion_90():
    result = probe_clip(Path("/shooting/vertical.MP4"), runner=lambda path: FFPROBE_JSON_VERTICAL_SIDE_DATA)
    assert result["width"] == 2160
    assert result["height"] == 3840
    assert result["rotation"] == 90


def test_probe_clip_vertical_por_tag_rotate_viejo():
    result = probe_clip(Path("/shooting/vertical_viejo.MP4"), runner=lambda path: FFPROBE_JSON_VERTICAL_TAG_VIEJO)
    assert result["width"] == 1080
    assert result["height"] == 1920
    assert result["rotation"] == 270


def test_probe_clip_horizontal_sin_rotacion_no_intercambia():
    result = probe_clip(Path("/shooting/horizontal.MP4"), runner=lambda path: FFPROBE_JSON_HORIZONTAL_SIN_ROTACION)
    assert result["width"] == 1920
    assert result["height"] == 1080
    assert result["rotation"] == 0


# --- orientacion (F9) ---------------------------------------------------
#
# Hasta la F9 el manifest declaraba `orientacion="horizontal"` escrito a
# mano, y el material de Bruno es mayoria VERTICAL: la secuencia salia con
# la forma equivocada en Premiere. El dato ya estaba en la app -- probe.py
# lo devuelve corregido por rotacion desde la F1 -- solo no lo usaba nadie.


def test_orientacion_de_un_tamano():
    assert orientacion_de(2160, 3840) == "vertical"
    assert orientacion_de(3840, 2160) == "horizontal"


def test_un_clip_cuadrado_no_es_vertical():
    assert orientacion_de(1080, 1080) == "horizontal"


def test_la_predominante_es_la_mayoria():
    assert orientacion_predominante([(2160, 3840), (2160, 3840), (3840, 2160)]) == "vertical"
    assert orientacion_predominante([(3840, 2160), (3840, 2160), (2160, 3840)]) == "horizontal"


def test_el_empate_se_va_a_vertical():
    """No es capricho: el material de Bruno es mayoria vertical, y una
    secuencia vertical con un clip horizontal adentro se arregla en
    Premiere; al reves, el clip vertical se recorta."""
    assert orientacion_predominante([(2160, 3840), (3840, 2160)]) == "vertical"


def test_sin_ningun_tamano_conocido_queda_el_default_de_siempre():
    """Pasa de verdad: una sesion restaurada de disco no vuelve a correr
    ffprobe, asi que no hay un solo tamaño. Ahi no se adivina -- se deja
    lo que la app declaraba antes de la F9."""
    assert orientacion_predominante([]) == "horizontal"


def test_los_tamanos_en_cero_no_cuentan():
    assert orientacion_predominante([(0, 0), (2160, 3840)]) == "vertical"
    assert orientacion_predominante([(0, 0)]) == "horizontal"
