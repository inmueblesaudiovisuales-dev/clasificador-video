# tests/test_proxy_match.py
from pathlib import Path

from clasificador_video.proxy_match import match_proxies


def test_empareja_por_stem_mas_sufijo_s03():
    originales = [Path("/cam/20260804_PIB0587.MP4")]
    proxies = [Path("/proxies/20260804_PIB0587S03.MP4")]
    result = match_proxies(originales, proxies)
    assert result[Path("/cam/20260804_PIB0587.MP4")] == Path("/proxies/20260804_PIB0587S03.MP4")


def test_original_sin_proxy_correspondiente_queda_none():
    originales = [Path("/cam/DJI_0001.MP4")]
    proxies: list[Path] = []
    result = match_proxies(originales, proxies)
    assert result[Path("/cam/DJI_0001.MP4")] is None


def test_no_confunde_prefijos_parecidos():
    originales = [Path("/cam/C001.MP4"), Path("/cam/C0010.MP4")]
    proxies = [Path("/proxies/C0010S03.MP4")]
    result = match_proxies(originales, proxies)
    assert result[Path("/cam/C001.MP4")] is None
    assert result[Path("/cam/C0010.MP4")] == Path("/proxies/C0010S03.MP4")
