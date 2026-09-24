"""Leer y escribir un ``.prproj`` (XML comprimido con gzip). Sin Qt."""
from __future__ import annotations

import gzip
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path


def leer_prproj(ruta: Path) -> ET.Element:
    """El elemento raíz ``<PremiereData>`` de un ``.prproj``."""
    with gzip.open(ruta, "rb") as archivo:
        return ET.fromstring(archivo.read())


def escribir_prproj(raiz: ET.Element, destino: Path) -> None:
    """Comprime ``raiz`` como gzip y lo escribe en ``destino``.

    Los caracteres no ASCII (acentos, ``✓``, ``★``, ``✕``) se escriben como
    UTF-8 de verdad y no como entidades ``&#...;``: Premiere muestra la
    entidad tal cual en los nombres de bins y clips, no la decodifica.
    """
    cuerpo = (
        '<?xml version="1.0" encoding="UTF-8" ?>\n'
        + ET.tostring(raiz, encoding="unicode")
    ).encode("utf-8")
    with gzip.open(destino, "wb") as archivo:
        archivo.write(cuerpo)


class AsignadorDeIds:
    """Entrega IDs y GUIDs que no chocan con los ya presentes."""

    def __init__(self, raiz: ET.Element):
        maximo = 0
        for elemento in raiz.iter():
            for atributo in ("ObjectID", "ObjectRef"):
                valor = elemento.get(atributo)
                if valor is not None and valor.isdigit():
                    maximo = max(maximo, int(valor))
        self._siguiente = maximo + 1

    def nuevo_object_id(self) -> str:
        valor = str(self._siguiente)
        self._siguiente += 1
        return valor

    def nuevo_object_uid(self) -> str:
        return str(uuid.uuid4())


_PARES = {"ObjectID": "ObjectRef", "ObjectUID": "ObjectURef"}


def _referencias_de(elemento: ET.Element):
    for hijo in elemento.iter():
        for ancla, ref in _PARES.items():
            valor = hijo.get(ref)
            if valor is not None:
                yield ancla, valor


def clonar_por_cierre(
    raiz: ET.Element,
    tipo_ancla: str,
    valor_ancla: str,
    asignador: AsignadorDeIds,
    fronteras: set[tuple[str, str]] = frozenset(),
) -> dict[tuple[str, str], ET.Element]:
    """Clona un objeto y su cierre de referencias como hermanos de raíz."""
    indice = {
        (ancla, valor): elemento
        for elemento in raiz
        for ancla in _PARES
        if (valor := elemento.get(ancla)) is not None
    }
    por_visitar = [(tipo_ancla, valor_ancla)]
    vistos: set[tuple[str, str]] = set()
    orden: list[tuple[str, str]] = []
    ids: dict[tuple[str, str], tuple[str, str]] = {}
    while por_visitar:
        clave = por_visitar.pop()
        if clave in vistos or clave in fronteras:
            continue
        vistos.add(clave)
        if clave not in indice:
            continue
        orden.append(clave)
        ancla, _ = clave
        ids[clave] = (ancla, asignador.nuevo_object_id() if ancla == "ObjectID" else asignador.nuevo_object_uid())
        por_visitar.extend(_referencias_de(indice[clave]))

    resultado = {}
    for clave in orden:
        clon = ET.fromstring(ET.tostring(indice[clave]))
        ancla, nuevo = ids[clave]
        clon.set(ancla, nuevo)
        for hijo in clon.iter():
            for anc, ref in _PARES.items():
                valor = hijo.get(ref)
                if valor is not None and (anc, valor) in ids:
                    hijo.set(ref, ids[(anc, valor)][1])
        raiz.append(clon)
        resultado[clave] = clon
    return resultado
