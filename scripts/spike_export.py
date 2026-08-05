"""Genera un xmeml de prueba a partir de 2-3 clips reales, para validar
manualmente el import en Premiere Pro. Edita MANIFEST antes de correr:
cada entrada es (ruta_absoluta_al_clip, categoria_path, in_frame, out_frame, flag).

Uso:
    python scripts/spike_export.py

Genera `spike-output.xml` en el directorio actual.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from clasificador_video.models import ClipSpec
from clasificador_video.probe import probe_clip
from clasificador_video.xmeml import generate_xmeml

# EDITA ESTA LISTA con rutas reales de tu Mac antes de correr el script.
# category_path: lista de cuarto/subcuarto, ej. ["Recamara 2", "Bano"]
# in_frame/out_frame: None para usar el clip completo, o un entero de frame.
# flag: "none", "pick" o "reject".
MANIFEST = [
    ("/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO/TEST/20260804_PIB0587.MP4", ["Cocina"], None, None, "pick"),
    ("/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO/TEST/20260804_PIB0588.MP4", ["Recamara 2", "Bano"], None, None, "reject"),
    ("/Users/brunogutierrez/Documents/CLAUDE CODE/ORGANIZADOR VIDEO/TEST/20260804_PIB0589.MP4", ["Sala"], 30, 200, "none"),
]


def main() -> None:
    clips = []
    for file_path, category_path, in_frame, out_frame, flag in MANIFEST:
        path = Path(file_path)
        if not path.exists():
            raise SystemExit(f"No existe el archivo: {path}")
        metadata = probe_clip(path)
        clips.append(
            ClipSpec(
                file_path=path,
                category_path=category_path,
                width=metadata["width"],
                height=metadata["height"],
                fps=metadata["fps"],
                has_audio=metadata["has_audio"],
                duration_frames=metadata["duration_frames"],
                in_frame=in_frame,
                out_frame=out_frame,
                flag=flag,
                rotation=metadata["rotation"],
            )
        )

    xml_str = generate_xmeml("Spike de validacion", clips)
    output_path = Path("spike-output.xml")
    output_path.write_text(xml_str, encoding="utf-8")
    print(f"Escrito: {output_path.resolve()}")


if __name__ == "__main__":
    main()
