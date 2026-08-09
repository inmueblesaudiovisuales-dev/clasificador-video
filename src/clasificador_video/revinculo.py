"""Reencontrar el material cuando el proyecto se abre en otro lado.

Dos pasos, y el segundo es el que importa: **buscar** un candidato, y
**confirmar** que es el archivo que era. Las camaras renumeran desde cero
en cada tarjeta --la Sony escribe `C0001.MP4` en todas-- asi que el nombre
solo no alcanza: enganchar el archivo equivocado es peor que no
encontrarlo, porque nadie se entera.

Sin Qt.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# cuantos cuadros de diferencia se toleran al confirmar. El mismo margen
# que usa `_el_proxy_calza`: ffprobe redondea distinto segun el contenedor.
TOLERANCIA_DE_CUADROS = 1


def buscar_bajo(carpeta: Path, relativa: str) -> Path | None:
    """Primero donde decia; si no, por nombre en todo el arbol.

    Devuelve `None` cuando hay mas de un candidato con ese nombre: ahi
    elegir seria adivinar, y adivinar es justo el modo de falla que este
    modulo existe para evitar.
    """
    if not carpeta.is_dir():
        return None
    en_su_sitio = carpeta / relativa
    if en_su_sitio.is_file():
        return en_su_sitio
    nombre = Path(relativa).name
    candidatos = [p for p in carpeta.rglob(nombre) if p.is_file()]
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
    """
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
    except Exception:
        # Un archivo que ffprobe no puede leer no es «el que era»: es un
        # archivo roto con el nombre correcto.
        return False
    cuadros = int((info or {}).get("duration_frames") or 0)
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
