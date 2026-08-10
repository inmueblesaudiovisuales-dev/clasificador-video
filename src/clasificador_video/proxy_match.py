# src/clasificador_video/proxy_match.py
#
# Los proxies se enganchan A MANO, como el «Attach Proxies» de Premiere:
# eliges el proxy de un clip y de ese par sale el patron de nombre para
# todos los demas. La busqueda automatica que vivia aca --recorrer las
# carpetas de alrededor buscando archivos terminados en `S03`-- se quito
# por pedido de Bruno: «necesito que los proxies los ponga manualmente
# siempre». Esta en el historial de git si algun dia hace falta.
from __future__ import annotations

from pathlib import Path

from clasificador_video.ingest import VIDEO_EXTENSIONS


def patron_de_proxy(original: Path, proxy_elegido: Path) -> tuple[str, str] | None:
    """De UN par (clip, su proxy) saca el patron de nombre: prefijo y sufijo.

    Es el corazon del enganche manual, el que Bruno pidio «como en
    Premiere: agarras un clip primero y luego se pone todo». De
    `C0001.MP4` + `C0001S03.MP4` sale `("", "S03")`, y con eso se buscan
    los otros 127.

    Devuelve `None` si el nombre elegido no contiene el del clip: eso
    significa que se eligio el archivo equivocado, y emparejar 128 clips
    con un patron inventado seria peor que no hacer nada.
    """
    original_stem, proxy_stem = original.stem, proxy_elegido.stem
    if original_stem not in proxy_stem:
        return None
    corte = proxy_stem.index(original_stem)
    return proxy_stem[:corte], proxy_stem[corte + len(original_stem):]


def clip_del_proxy(rutas: list[Path], proxy_elegido: Path) -> Path | None:
    """De todos los clips del bin, ¿a cual corresponde el proxy elegido?

    Existe porque el enganche pedia el proxy DEL CLIP EN EL QUE ESTABAS, y
    eso no se ve por ningun lado: abres el dialogo, ves una carpeta de 111
    proxies ordenados por nombre y eliges el primero. Bruno se topo con
    esto en su material -- «no puedo solo elegir el primer clip de la
    carpeta de proxies». El patron sale igual de bien de CUALQUIER par, asi
    que lo unico que hacia falta era averiguar de que par se trata.

    Gana el nombre mas largo que calce: `C0001` esta contenido en
    `C00011S03`, y con el corto se deduciria el sufijo equivocado (`1S03`)
    para los 110 restantes.
    """
    calzan = [r for r in rutas if r.stem and r.stem in proxy_elegido.stem]
    return max(calzan, key=lambda r: len(r.stem)) if calzan else None


def emparejar_con_patron(
    originales: list[Path], carpeta: Path, prefijo: str, sufijo: str,
    extension: str,
) -> dict[Path, Path | None]:
    """Aplica el patron a todos los clips, dentro de UNA carpeta.

    Se prueba primero la extension del proxy que se eligio, y despues
    cualquier otra de video: hay camaras que escriben el original en
    `.MP4` y el proxy en `.MOV`.
    """
    try:
        por_stem = {
            p.stem: p for p in carpeta.iterdir()
            if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS
        }
    except OSError:
        por_stem = {}   # la carpeta ya no esta, o no se puede leer

    resultado: dict[Path, Path | None] = {}
    for original in originales:
        buscado = f"{prefijo}{original.stem}{sufijo}"
        candidato = por_stem.get(buscado)
        # el `extension` no filtra, ORDENA: si hay dos con el mismo nombre
        # y distinta extension, gana la del proxy que se eligio
        if candidato is not None and candidato.suffix.lower() != extension.lower():
            mismo = carpeta / f"{buscado}{extension}"
            if mismo.exists():
                candidato = mismo
        resultado[original] = candidato
    return resultado


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
