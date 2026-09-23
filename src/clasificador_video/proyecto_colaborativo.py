"""Armar la carpeta de un proyecto colaborativo dentro de la carpeta de
iCloud de Bruno: negocio -> año -> mes -> folio, con sus 8 subcarpetas y
los templates de Premiere/AE copiados y renombrados.

Spec: docs/superpowers/specs/2026-09-23-proyecto-colaborativo-icloud-design.md

Sin Qt: esto solo parsea texto y toca el disco. Quien pregunta y confirma
con Bruno vive en `app.py` (`Coordinador._nuevo`).
"""
from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from clasificador_video import proyecto

# El folio ya es el nombre del proyecto en Clipify (ver `buscar_prproj.py`).
# Formato confirmado con Bruno: NEGOCIO-AAMM.DD-LETRA, por ejemplo
# "IAV-2609.10-A" -> negocio IAV, año 2026, mes 09, día 10, primer
# proyecto del día. El día y la letra no hacen falta para armar la ruta
# -- solo negocio, año y mes -- así que el patrón no los valida más allá
# de que existan con el formato correcto.
_PATRON_FOLIO = re.compile(r"^(IAV|PI)-(\d{2})(\d{2})\.(\d{2})-([A-Z])$")

# Nombre exacto de la carpeta de negocio dentro de la raíz de iCloud, tal
# como ya existen en el disco de Bruno.
NEGOCIOS = {"IAV": "01. IAV", "PI": "02. PI"}

# Nombre exacto de cada carpeta de mes, tal como ya existen en el disco de
# Bruno (índice 0 = enero).
MESES = (
    "01. Enero", "02. Febrero", "03. Marzo", "04. Abril", "05. Mayo",
    "06. Junio", "07. Julio", "08. Agosto", "09. Septiembre",
    "10. Octubre", "11. Noviembre", "12. Diciembre",
)

# Hermana de las carpetas de negocio, dentro de la raíz de iCloud.
CARPETA_TEMPLATES = "03. Templates"
TEMPLATE_PREMIERE_NOMBRE = "TemplatePremiere.prproj"
TEMPLATE_AE_NOMBRE = "TemplateAE.aep"

# Las 8 subcarpetas de todo proyecto colaborativo, en este orden. Los
# nombres son literales -- tal como los escribió Bruno, con sus mayúsculas
# y sin acentos donde él no los puso -- porque son carpetas que él ve en
# Finder todos los días.
SUBCARPETAS = (
    "01. Proyecto premiere",
    "02. Proyecto AE",
    "03. Proxies",
    "04. Musica",
    "05. Logos y graficos",
    "06. Voz IA",
    "07. guiones",
    "08. Clipify",
)
CARPETA_PREMIERE = SUBCARPETAS[0]
CARPETA_AE = SUBCARPETAS[1]
CARPETA_PROXIES = SUBCARPETAS[2]
CARPETA_CLIPIFY = SUBCARPETAS[7]


@dataclass(frozen=True)
class FolioPartido:
    negocio: str  # "IAV" o "PI"
    anio: int     # año completo, p.ej. 2026
    mes: int      # 1-12


def partir_folio(folio: str) -> FolioPartido | None:
    """El negocio, año y mes de un folio, o `None` si el texto no calza
    con el patrón (negocio que no es IAV/PI, o mes fuera de 1-12).

    No se adivina: un folio que no parsea se le devuelve a Bruno para que
    lo corrija, no se intenta interpretar a la fuerza.
    """
    m = _PATRON_FOLIO.match(folio.strip())
    if m is None:
        return None
    negocio, aa, mm, dd = m.group(1), m.group(2), m.group(3), m.group(4)
    mes = int(mm)
    if not 1 <= mes <= 12:
        return None
    anio = 2000 + int(aa)
    try:
        date(anio, mes, int(dd))
    except ValueError:
        return None
    return FolioPartido(negocio=negocio, anio=anio, mes=mes)


def ruta_del_proyecto(raiz: Path, folio: str) -> Path | None:
    """La ruta completa de la carpeta del proyecto dentro de `raiz` (la
    carpeta raíz de iCloud que Bruno configuró). `None` si el folio no
    parsea.

    Esta ruta puede no existir todavía en disco -- armarla es puro cálculo
    de texto, no toca el disco. Quien la crea es `crear_carpeta_de_proyecto`.
    """
    partido = partir_folio(folio)
    if partido is None:
        return None
    return (
        raiz / NEGOCIOS[partido.negocio] / str(partido.anio)
        / MESES[partido.mes - 1] / folio
    )


@dataclass(frozen=True)
class ResultadoDeCreacion:
    carpeta_proyecto: Path
    ruta_cvproj: Path
    ruta_prproj: Path
    ruta_aep: Path


def crear_carpeta_de_proyecto(carpeta_proyecto: Path, carpeta_templates: Path,
                              folio: str) -> ResultadoDeCreacion:
    """Crea la carpeta del folio con sus 8 subcarpetas y copia los templates
    ya renombrados con el folio.

    No crea nada a medias: revisa TODO antes de tocar el disco.

    `FileNotFoundError` -- con la ruta que faltó como mensaje -- si
    `carpeta_proyecto.parent` no existe (la carpeta de negocio/año/mes que
    Bruno arma a mano todavía no llega a ese mes) o si falta algún
    template.

    `FileExistsError` -- con la ruta que ya existía -- si la carpeta del
    folio ya existe. Bruno decide qué hacer con ella; esta función nunca
    escribe encima de algo que ya estaba ahí.
    """
    if not carpeta_proyecto.parent.is_dir():
        raise FileNotFoundError(str(carpeta_proyecto.parent))
    if carpeta_proyecto.exists():
        raise FileExistsError(str(carpeta_proyecto))
    template_premiere = carpeta_templates / TEMPLATE_PREMIERE_NOMBRE
    template_ae = carpeta_templates / TEMPLATE_AE_NOMBRE
    if not template_premiere.is_file():
        raise FileNotFoundError(str(template_premiere))
    if not template_ae.is_file():
        raise FileNotFoundError(str(template_ae))

    try:
        carpeta_proyecto.mkdir()
        for nombre in SUBCARPETAS:
            (carpeta_proyecto / nombre).mkdir()

        ruta_prproj = carpeta_proyecto / CARPETA_PREMIERE / f"{folio}.prproj"
        ruta_aep = carpeta_proyecto / CARPETA_AE / f"{folio}.aep"
        shutil.copyfile(template_premiere, ruta_prproj)
        shutil.copyfile(template_ae, ruta_aep)
    except OSError:
        shutil.rmtree(carpeta_proyecto, ignore_errors=True)
        raise
    ruta_cvproj = carpeta_proyecto / CARPETA_CLIPIFY / f"{folio}{proyecto.EXTENSION}"

    return ResultadoDeCreacion(
        carpeta_proyecto=carpeta_proyecto,
        ruta_cvproj=ruta_cvproj,
        ruta_prproj=ruta_prproj,
        ruta_aep=ruta_aep,
    )
