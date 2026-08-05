from pathlib import Path

from clasificador_video.models import ClipSpec


def _clip(**overrides) -> ClipSpec:
    base = dict(
        file_path=Path("/shooting/C0012.MP4"),
        category_path=["Cocina"],
        width=3840,
        height=2160,
        fps=29.97,
        has_audio=True,
        duration_frames=900,
    )
    base.update(overrides)
    return ClipSpec(**base)


def test_sin_in_out_usa_el_clip_completo():
    clip = _clip()
    assert clip.effective_in() == 0
    assert clip.effective_out() == 900


def test_con_in_out_usa_los_valores_marcados():
    clip = _clip(in_frame=120, out_frame=600)
    assert clip.effective_in() == 120
    assert clip.effective_out() == 600


def test_flag_por_defecto_es_none():
    clip = _clip()
    assert clip.flag == "none"
