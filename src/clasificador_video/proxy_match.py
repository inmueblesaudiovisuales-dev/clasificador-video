# src/clasificador_video/proxy_match.py
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from clasificador_video.ingest import SUFIJO_PROXY, VIDEO_EXTENSIONS, es_archivo_de_proxy

# Cuantos niveles se recorren desde la carpeta PADRE de la importada. Con 2
# alcanza para los dos casos reales -- el proxy suelto en el padre, y el
# proxy en una carpeta hermana (`clips/` + `proxy/`, `CLIP/` + `SUB/`) -- y
# sin tope, importar algo de la raiz de una tarjeta recorreria el volumen
# entero.
PROFUNDIDAD_DE_BUSQUEDA = 2


def match_proxies(originales: list[Path], proxies: list[Path]) -> dict[Path, Path | None]:
    """Empareja cada original con su proxy por 'mismo stem + S03' (spec §3).

    Ej: 20260804_PIB0587.MP4 <-> 20260804_PIB0587S03.MP4. Sin match, None
    -- no es error (dron y otras fuentes sin proxy son el caso normal).
    """
    corte = -len(SUFIJO_PROXY)
    proxy_by_stem: dict[str, Path] = {
        p.stem[:corte]: p for p in proxies if es_archivo_de_proxy(p)
    }
    return {original: proxy_by_stem.get(original.stem) for original in originales}


def buscar_proxies(carpeta_importada: Path) -> list[Path]:
    """Junta los candidatos a proxy alrededor de una carpeta importada.

    `match_proxies()` recibe dos listas ya armadas, y hasta la F9 nadie las
    armaba. Buscarlas es su propio problema porque **el proxy casi nunca
    esta donde estan los originales**: Bruno los guarda en una carpeta
    aparte (`clips/` y `proxy/`), y la tarjeta de la FX30 hace lo mismo
    (`CLIP/` y `SUB/`). Por eso se busca desde la carpeta PADRE de la
    importada y no desde la importada.

    Nunca levanta: una carpeta sin permisos o que ya no esta devuelve lo
    que se pudo leer. Importar de un volumen ajeno no puede tumbar la app.
    """
    raiz = carpeta_importada.parent
    return sorted(
        ruta
        for ruta in _archivos_hasta(raiz, PROFUNDIDAD_DE_BUSQUEDA)
        if ruta.suffix.lower() in VIDEO_EXTENSIONS and es_archivo_de_proxy(ruta)
    )


def etiqueta_de_resolucion(ancho: int, alto: int) -> str:
    """`1280x720` → `"720p"`, mirando el **lado corto**: un proxy vertical
    de 1080x1920 es 1080p, no 1920p.

    La usan el badge sobre el video y el contador de la barra de estado.
    Que sea una sola funcion no es cosmetica -- dos vistas del mismo dato
    en este proyecto ya se contradijeron cinco veces.
    """
    if ancho <= 0 or alto <= 0:
        return ""
    return f"{min(ancho, alto)}p"


def _archivos_hasta(raiz: Path, profundidad: int) -> Iterator[Path]:
    if profundidad <= 0:
        return
    try:
        entradas = sorted(raiz.iterdir())
    except OSError:
        return  # sin permisos, o la carpeta ya no esta
    for entrada in entradas:
        try:
            es_carpeta = entrada.is_dir()
        except OSError:
            continue
        if es_carpeta:
            yield from _archivos_hasta(entrada, profundidad - 1)
        else:
            yield entrada
