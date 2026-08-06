# src/clasificador_video/proxy_match.py
from __future__ import annotations

from pathlib import Path


def match_proxies(originales: list[Path], proxies: list[Path]) -> dict[Path, Path | None]:
    """Empareja cada original con su proxy por 'mismo stem + S03' (spec §3).

    Ej: 20260804_PIB0587.MP4 <-> 20260804_PIB0587S03.MP4. Sin match, None
    -- no es error (dron y otras fuentes sin proxy son el caso normal).
    """
    proxy_by_stem: dict[str, Path] = {p.stem[:-3]: p for p in proxies if p.stem.endswith("S03")}
    return {original: proxy_by_stem.get(original.stem) for original in originales}
