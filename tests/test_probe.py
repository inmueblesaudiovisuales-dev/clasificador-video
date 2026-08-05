import json
from pathlib import Path

import pytest

from clasificador_video.probe import probe_clip

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
