"""Leer y escribir un ``.prproj`` (XML comprimido con gzip). Sin Qt."""
from __future__ import annotations

import gzip
import xml.etree.ElementTree as ET
from pathlib import Path


def leer_prproj(ruta: Path) -> ET.Element:
    """El elemento raíz ``<PremiereData>`` de un ``.prproj``."""
    with gzip.open(ruta, "rb") as archivo:
        return ET.fromstring(archivo.read())


def escribir_prproj(raiz: ET.Element, destino: Path) -> None:
    """Comprime ``raiz`` como gzip y lo escribe en ``destino``."""
    cuerpo = b'<?xml version="1.0" encoding="UTF-8" ?>\n' + ET.tostring(raiz)
    with gzip.open(destino, "wb") as archivo:
        archivo.write(cuerpo)
