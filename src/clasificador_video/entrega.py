"""El estado de la entrega de un proyecto a un editor externo por Drive.

Vive aparte de `proyecto.py` porque `proyecto.py` sabe la FORMA del
documento entero y este módulo sabe solo esta pieza -- igual que
`manifest.py` no sabe nada del `.cvproj`.

Cuatro estados nada más, en el orden en que pasan:

- `SIN_SUBIR` -- nunca se subió nada (o es un proyecto de antes de esta
  función: no hay diferencia).
- `CON_EDITOR` -- ya se subió; no se sabe si el editor contestó porque
  esa pregunta es siempre a petición de Bruno (nunca automática al abrir
  la app -- spec de interfaz, §4).
- `EDITOR_CONTESTO` -- Bruno pidió revisar (el ⟳ de la lista, o el
  diálogo de "Traer de vuelta") y Drive tenía algo nuevo.
- `EN_REVISION` -- Bruno ya trajo el corte del editor y lo está
  revisando. Si sube una versión nueva vuelve a `CON_EDITOR`; cuando el
  cliente aprueba, Bruno marca "Ya entregado" y la entrega se limpia
  (spec 2026-09-19).

Sin Qt, sin red: esto solo carga y guarda el estado. Quien pregunta a
Drive de verdad es `drive.py`.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EstadoEntrega:
    SIN_SUBIR = "sin_subir"
    CON_EDITOR = "con_editor"
    EDITOR_CONTESTO = "editor_contesto"
    # Traer de vuelta ya NO limpia la entrega (spec 2026-09-19): deja al
    # proyecto aquí, esperando que Bruno decida si sube de nuevo o marca
    # "Ya entregado". Antes de este estado, "Traer de vuelta" ponía
    # `self._entrega = None` -- ver MainWindow._on_drive_traida_lista.
    EN_REVISION = "en_revision"

    estado: str
    subido_en: str | None = None
    prproj_local: str | None = None
    drive_folder_id: str | None = None
    drive_folder_link: str | None = None
    # La fecha de modificación del .prproj en Drive TAL COMO ESTABA cuando
    # se subió por última vez. Es contra lo que se compara al revisar si
    # el editor ya contestó -- ver `drive.hay_cambios`.
    drive_prproj_modificado_en: str | None = None

    def to_dict(self) -> dict:
        return {
            "estado": self.estado,
            "subido_en": self.subido_en,
            "prproj_local": self.prproj_local,
            "drive_folder_id": self.drive_folder_id,
            "drive_folder_link": self.drive_folder_link,
            "drive_prproj_modificado_en": self.drive_prproj_modificado_en,
        }

    @staticmethod
    def de_dict(datos: dict | None) -> "EstadoEntrega | None":
        if not datos:
            return None
        return EstadoEntrega(
            estado=datos.get("estado", EstadoEntrega.SIN_SUBIR),
            subido_en=datos.get("subido_en"),
            prproj_local=datos.get("prproj_local"),
            drive_folder_id=datos.get("drive_folder_id"),
            drive_folder_link=datos.get("drive_folder_link"),
            drive_prproj_modificado_en=datos.get("drive_prproj_modificado_en"),
        )


def cerrar_en_archivo(ruta_cvproj: Path) -> bool:
    """El botón "Ya entregado": limpia la entrega guardada en un `.cvproj`
    sin abrir el proyecto y SIN tocar Drive -- a diferencia de "Traer de
    vuelta", esto es solo una marca de organización de Bruno (spec
    2026-09-19 §6). `False` si no había nada que limpiar o el archivo no
    se pudo leer.
    """
    import json

    from clasificador_video import proyecto

    try:
        data = json.loads(ruta_cvproj.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not data.get("entrega"):
        return False
    data["entrega"] = None
    proyecto.guardar(ruta_cvproj, data)
    return True
