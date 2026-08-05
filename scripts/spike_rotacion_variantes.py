"""Diagnostico: cuanta informacion de medios podemos DEJAR DE declarar en el
<file> antes de que Premiere sondee el archivo por su cuenta (y aplique solo
la rotacion de despliegue del contenedor).

Contexto: el vocabulario del parser xmeml de Premiere (extraido de su binario)
no tiene ninguna etiqueta de rotacion/orientacion a nivel de archivo, y el
modelo FootageInterpretation de Premiere tampoco expone rotacion. O sea: la
UNICA via para que un clip maestro quede derecho es que Premiere lea la matriz
de despliegue del archivo el mismo. Este script arma cinco variantes del mismo
clip (cada una apuntando a una COPIA fisica distinta, para que Premiere no las
deduplique ni reuse cache entre variantes) que declaran cada vez menos.

Uso:
    python scripts/spike_rotacion_variantes.py

Genera TEST/rotacion/rotacion-variantes.xml. Importarlo en Premiere y ver
cual de los cinco bins muestra el clip DERECHO (vertical) en el monitor de
origen.
"""

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from clasificador_video.probe import probe_clip
from clasificador_video.xmeml import _audio_block_xml, _pathurl, _rate_xml, _xml_text

VARIANTES_DIR = Path(__file__).resolve().parent.parent / "TEST" / "rotacion"

# (letra, descripcion para el nombre del bin)
VARIANTES = [
    ("A", "A - file sin bloque media"),
    ("B", "B - media/video vacio (sin samplecharacteristics)"),
    ("C", "C - samplecharacteristics sin width/height"),
    ("D", "D - CONTROL: declaracion completa 2160x3840"),
    ("E", "E - file minimo: solo name + pathurl"),
]


def _file_xml(letra: str, path: Path, meta: dict) -> str:
    file_id = f"file-{letra}"
    audio_xml = ""
    if meta["has_audio"]:
        audio_xml = _audio_block_xml(1, "left") + _audio_block_xml(2, "right")

    cabecera = (
        f'<file id="{file_id}">'
        f"<name>{_xml_text(path.name)}</name>"
        f"<pathurl>{_pathurl(path)}</pathurl>"
    )
    rate_y_duracion = f"{_rate_xml(meta['fps'])}<duration>{meta['duration_frames']}</duration>"

    if letra == "E":
        return cabecera + "</file>"
    if letra == "A":
        return cabecera + rate_y_duracion + "</file>"
    if letra == "B":
        return cabecera + rate_y_duracion + f"<media><video></video>{audio_xml}</media></file>"
    if letra == "C":
        return (
            cabecera
            + rate_y_duracion
            + "<media><video><samplecharacteristics>"
            + _rate_xml(meta["fps"])
            + "<anamorphic>FALSE</anamorphic><pixelaspectratio>square</pixelaspectratio>"
            "<fielddominance>none</fielddominance>"
            f"</samplecharacteristics></video>{audio_xml}</media></file>"
        )
    # D: control, exactamente lo que genera hoy xmeml.py
    return (
        cabecera
        + rate_y_duracion
        + "<media><video><samplecharacteristics>"
        + _rate_xml(meta["fps"])
        + f"<width>{meta['width']}</width><height>{meta['height']}</height>"
        "<anamorphic>FALSE</anamorphic><pixelaspectratio>square</pixelaspectratio>"
        "<fielddominance>none</fielddominance>"
        f"</samplecharacteristics></video>{audio_xml}</media></file>"
    )


def _bin_xml(letra: str, descripcion: str, path: Path, meta: dict) -> str:
    masterclip_id = f"masterclip-{letra}"
    clipitem_xml = (
        f'<clipitem id="clipitem-{letra}">'
        f"<masterclipid>{masterclip_id}</masterclipid>"
        f"<name>{_xml_text(path.stem)}</name>"
        f"{_rate_xml(meta['fps'])}"
        f"<in>0</in><out>{meta['duration_frames']}</out>"
        "<alphatype>none</alphatype>"
        "<pixelaspectratio>square</pixelaspectratio>"
        "<anamorphic>FALSE</anamorphic>"
        f"{_file_xml(letra, path, meta)}"
        "</clipitem>"
    )
    clip_xml = (
        f'<clip id="{masterclip_id}" explodedTracks="true">'
        f"<uuid>{uuid.uuid4()}</uuid>"
        f"<masterclipid>{masterclip_id}</masterclipid>"
        "<ismasterclip>TRUE</ismasterclip>"
        f"<duration>{meta['duration_frames']}</duration>"
        f"{_rate_xml(meta['fps'])}"
        f"<name>{_xml_text(path.stem)}</name>"
        f"<media><video><track>{clipitem_xml}</track></video></media>"
        "</clip>"
    )
    return (
        f"<bin><name>{_xml_text(descripcion)}</name>"
        f"<children>{clip_xml}</children></bin>"
    )


def main() -> None:
    bins = []
    for letra, descripcion in VARIANTES:
        path = VARIANTES_DIR / f"VARIANTE-{letra}.MP4"
        if not path.exists():
            raise SystemExit(f"Falta la copia de prueba: {path}")
        meta = probe_clip(path)
        bins.append(_bin_xml(letra, descripcion, path, meta))

    # La secuencia va vacia y vertical, igual que el export real.
    rate_xml = _rate_xml(60000 / 1001)
    sequence_xml = (
        '<sequence id="sequence-1">'
        f"<uuid>{uuid.uuid4()}</uuid><duration>0</duration>{rate_xml}"
        "<name>Diagnostico rotacion</name>"
        "<media><video><format><samplecharacteristics>"
        f"{rate_xml}<width>2160</width><height>3840</height>"
        "<anamorphic>FALSE</anamorphic><pixelaspectratio>square</pixelaspectratio>"
        "<fielddominance>none</fielddominance><colordepth>24</colordepth>"
        "</samplecharacteristics></format>"
        "<track><enabled>TRUE</enabled><locked>FALSE</locked></track>"
        "</video></media>"
        f"<timecode>{rate_xml}<string>00;00;00;00</string><frame>0</frame>"
        "<displayformat>DF</displayformat></timecode>"
        "</sequence>"
    )

    xml_str = (
        '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n'
        '<xmeml version="4">'
        "<bin><name>Diagnostico rotacion vertical</name>"
        f"<children>{''.join(bins)}{sequence_xml}</children></bin>"
        "</xmeml>"
    )

    output_path = VARIANTES_DIR / "rotacion-variantes.xml"
    output_path.write_text(xml_str, encoding="utf-8")
    print(f"Escrito: {output_path}")


if __name__ == "__main__":
    main()
