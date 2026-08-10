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

from clasificador_video import proyecto

_log = logging.getLogger(__name__)

# cuantos cuadros de diferencia se toleran al confirmar. El mismo margen
# que usa `_el_proxy_calza`: ffprobe redondea distinto segun el contenedor.
TOLERANCIA_DE_CUADROS = 1


def cuadros_esperados_de(duraciones: dict, fps: dict) -> dict[int, int]:
    """El puente entre lo que el proyecto guarda y lo que `calza` compara.

    El documento guarda la duracion en **segundos** y aqui se confirma en
    **cuadros**. Sin este puente pasa una de dos: o media confirmacion no se
    cablea nunca, o alguien pasa segundos donde van cuadros y entonces no
    confirma jamas nada -- las dos terminan con Bruno sin poder reconectar.

    Redondea igual que `_el_proxy_calza`, que ya compara asi contra el
    original. Lo que no tenga los dos datos queda fuera: es mejor confirmar
    solo por peso que comparar contra un numero inventado.
    """
    segundos_por_clip = proyecto.por_indice_de_clip(duraciones)
    fps_por_clip = proyecto.por_indice_de_clip(fps)
    cuadros: dict[int, int] = {}
    for clip, segundos in segundos_por_clip.items():
        cuadros_por_segundo = fps_por_clip.get(clip)
        try:
            total = round(float(segundos) * float(cuadros_por_segundo))
        except (TypeError, ValueError):
            continue
        if total > 0:
            cuadros[clip] = total
    return cuadros


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


def faltantes_de(rutas: dict[int, Path]) -> list[int]:
    """Que clips ya no tienen su archivo en disco.

    Recibe y devuelve **indices de clip**, como todo el resto del modulo.
    Antes tomaba una lista y devolvia posiciones, que en un bin cualquiera
    no son los mismos numeros -- y confundir unos con otros termina
    reconectando el clip equivocado.
    """
    return sorted(i for i, ruta in rutas.items() if not Path(ruta).is_file())


def _identidad(ruta: Path):
    """Con que se decide si dos candidatos son el mismo archivo.

    Por inodo y no por texto: la misma copia puede aparecer escrita de dos
    formas --una por la ruta que decia el proyecto y otra por el indice, y
    en APFS con otras mayusculas-- y como texto se verian distintas.
    """
    try:
        info = ruta.stat()
        return (info.st_dev, info.st_ino)
    except OSError:
        return str(ruta)


def reencontrar_bin(carpeta: Path, relativas: dict[int, str],
                    bytes_esperados: dict[int, int],
                    cuadros_esperados: dict[int, int], medir) -> Reencuentro:
    """Buscar y confirmar, clip por clip, bajo la carpeta nueva del bin.

    Lo que no confirma no se engancha: se devuelve aparte para poder
    decirlo. Enganchar el archivo equivocado seria peor, porque nadie se
    entera.
    """
    indice = indice_de_nombres(carpeta)
    reconectados: dict[int, Path] = {}
    sin_confirmar: list[int] = []
    no_encontrados: list[int] = []
    for clip, relativa in relativas.items():
        candidato = buscar_bajo(carpeta, relativa, indice)
        if candidato is None:
            no_encontrados.append(clip)
        elif calza(candidato, bytes_esperados.get(clip),
                   cuadros_esperados.get(clip), medir):
            reconectados[clip] = candidato
        else:
            sin_confirmar.append(clip)
    for clip in _reclamados_por_mas_de_un_clip(reconectados):
        del reconectados[clip]
        sin_confirmar.append(clip)
    return Reencuentro(reconectados, sorted(sin_confirmar), sorted(no_encontrados))


def _reclamados_por_mas_de_un_clip(reconectados: dict[int, Path]) -> list[int]:
    """Un archivo no puede ser dos clips distintos.

    Cada clip se resuelve por su cuenta, asi que dos podian quedarse con la
    misma copia: dos tarjetas con su `C0001.MP4` cada una, y en el disco
    nuevo sobrevivio una sola. Bruno terminaba con dos clips que son el
    mismo video, con marcas distintas cada uno y nada que se lo dijera.
    Cuando pasa, ninguno de los dos se engancha.
    """
    duenos: dict[object, list[int]] = {}
    for clip, ruta in reconectados.items():
        duenos.setdefault(_identidad(ruta), []).append(clip)
    return [clip for clips in duenos.values() if len(clips) > 1 for clip in clips]
