from pathlib import Path
from urllib.parse import quote

from clasificador_video.rate import rate_for_fps


def _rate_xml(fps: float) -> str:
    timebase, ntsc = rate_for_fps(fps)
    return f"<rate><timebase>{timebase}</timebase><ntsc>{'TRUE' if ntsc else 'FALSE'}</ntsc></rate>"


def _pathurl(path: Path) -> str:
    encoded = quote(str(path))
    return f"file://localhost{encoded}"
