"""Reencontrar el material cuando el proyecto se abre en otro lado.

Dos pasos, y el segundo es el que importa: **buscar** un candidato, y
**confirmar** que es el archivo que era. Las camaras renumeran desde cero
en cada tarjeta --la Sony escribe `C0001.MP4` en todas-- asi que el nombre
solo no alcanza: enganchar el archivo equivocado es peor que no
encontrarlo, porque nadie se entera.

Sin Qt.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

_log = logging.getLogger(__name__)

# cuantos cuadros de diferencia se toleran al confirmar. El mismo margen
# que usa `_el_proxy_calza`: ffprobe redondea distinto segun el contenedor.
TOLERANCIA_DE_CUADROS = 1


def indice_de_nombres(carpeta: Path) -> dict[str, list[Path]]:
    """Un solo recorrido del arbol: de nombre de archivo a rutas.

    Buscar cada clip por su cuenta significaba recorrer entero el disco de
    Bruno una vez POR CLIP --con los 109 de una tarjeta de la Sony, 109
    recorridos de 128 GB-- y eso pasa en el hilo de la interfaz, con la
    ventana congelada y sin explicacion.

    Los nombres se comparan literales y en minusculas: `rglob(nombre)` los
    trataba como patron, y ahi `C0001[1].MP4` matchea con `C00011.MP4`, que
    es otro archivo. Las minusculas emparejan este camino con la busqueda
    literal, que en APFS ya ignoraba mayusculas.
    """
    indice: dict[str, list[Path]] = {}
    if not carpeta.is_dir():
        return indice
    for ruta in carpeta.rglob("*"):
        try:
            if ruta.is_file():
                indice.setdefault(ruta.name.casefold(), []).append(ruta)
        except OSError:
            continue  # un enlace roto o un permiso no corta la busqueda
    return indice


def _en_su_sitio(carpeta: Path, relativa: str) -> Path | None:
    """La ruta que el proyecto decia, si sigue colgando de la carpeta.

    La relativa sale de un `.cvproj`, que es dato externo: pudo escribirla
    una version anterior al filtro, o editarse a mano. Una absoluta hace que
    `carpeta / relativa` devuelva la absoluta, y un `..` se sale del arbol;
    en los dos casos se engancharia algo que Bruno no señalo.
    """
    pedazo = Path(relativa)
    if not pedazo.parts or pedazo.is_absolute() or ".." in pedazo.parts:
        return None
    destino = carpeta / pedazo
    return destino if destino.is_file() else None


def buscar_bajo(carpeta: Path, relativa: str,
                indice: dict[str, list[Path]] | None = None) -> Path | None:
    """Primero donde decia; si no, por nombre en todo el arbol.

    Devuelve `None` cuando hay mas de un candidato con ese nombre: ahi
    elegir seria adivinar, y adivinar es justo el modo de falla que este
    modulo existe para evitar.

    `indice` se pasa ya armado cuando se reencuentran varios clips de una
    misma carpeta, para no recorrerla una vez por clip.
    """
    if not carpeta.is_dir():
        return None
    en_su_sitio = _en_su_sitio(carpeta, relativa)
    if en_su_sitio is not None:
        return en_su_sitio
    nombre = Path(relativa).name
    if not nombre:
        return None
    if indice is None:
        indice = indice_de_nombres(carpeta)
    candidatos = indice.get(nombre.casefold(), [])
    return candidatos[0] if len(candidatos) == 1 else None


def calza(archivo: Path, tamano_esperado: int | None,
          cuadros_esperados: int | None, medir) -> bool:
    """¿Este archivo es el que el proyecto tenia?

    `medir` es la funcion que lee el video (en la app, `probe_clip`); se
    inyecta para poder probar esto sin ffprobe.

    El tamaño solo ya descarta al tocayo de otra tarjeta. Los cuadros se
    comprueban ADEMAS cuando el proyecto los sabia, porque dos tomas de la
    misma duracion pesan distinto pero dos archivos del mismo peso podrian
    ser el mismo material recodificado.

    Sin ningun dato guardado **no confirma**: dar por bueno lo que no se
    pudo comprobar es al reves de lo que este modulo promete.
    """
    if tamano_esperado is None and cuadros_esperados is None:
        return False
    if not archivo.is_file():
        return False
    if tamano_esperado is not None:
        try:
            if archivo.stat().st_size != tamano_esperado:
                return False
        except OSError:
            return False
    if cuadros_esperados is None:
        return True
    try:
        info = medir(archivo)
    except OSError:
        # Un archivo que ffprobe no puede leer no es «el que era»: es un
        # archivo roto con el nombre correcto. Es esperado, y va callado.
        return False
    except Exception:
        # Esto ya no es un archivo roto sino un `medir` mal conectado, y sin
        # rastro se ve identico: nada se reconecta y ni una pista de por que.
        _log.warning("`medir` fallo al confirmar %s", archivo, exc_info=True)
        return False
    crudo = (info or {}).get("duration_frames")
    if crudo is None:
        # «No se pudo medir» no es «dura cero cuadros». Colapsarlos hacia que
        # un clip de cero o un cuadro lo confirmara cualquier archivo ilegible.
        return False
    try:
        cuadros = int(crudo)
    except (TypeError, ValueError):
        return False
    return abs(cuadros - cuadros_esperados) <= TOLERANCIA_DE_CUADROS


@dataclass
class Reencuentro:
    """Los tres finales posibles, separados a proposito.

    `sin_confirmar` NO es lo mismo que `no_encontrados`: ahi hay un archivo
    con el nombre correcto que **no es** el que era, y eso hay que
    decirselo a Bruno con otras palabras --es el caso de la segunda tarjeta
    de la misma camara-- en vez de mezclarlo con «no aparecio».
    """
    reconectados: dict[int, Path]
    sin_confirmar: list[int]
    no_encontrados: list[int]


def faltantes_de(rutas: list[Path]) -> list[int]:
    """Que posiciones de la lista ya no tienen archivo en disco."""
    return [i for i, r in enumerate(rutas) if not Path(r).is_file()]


def reencontrar_bin(carpeta: Path, relativas: dict[int, str],
                    bytes_esperados: dict[int, int],
                    cuadros_esperados: dict[int, int], medir) -> Reencuentro:
    """Buscar y confirmar, clip por clip, bajo la carpeta nueva del bin.

    Lo que no confirma no se engancha: se devuelve aparte para poder
    decirlo. Enganchar el archivo equivocado seria peor, porque nadie se
    entera.
    """
    reconectados: dict[int, Path] = {}
    sin_confirmar: list[int] = []
    no_encontrados: list[int] = []
    for indice, relativa in relativas.items():
        candidato = buscar_bajo(carpeta, relativa)
        if candidato is None:
            no_encontrados.append(indice)
        elif calza(candidato, bytes_esperados.get(indice),
                   cuadros_esperados.get(indice), medir):
            reconectados[indice] = candidato
        else:
            sin_confirmar.append(indice)
    return Reencuentro(reconectados, sorted(sin_confirmar), sorted(no_encontrados))
