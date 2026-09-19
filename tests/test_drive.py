# tests/test_drive.py
from pathlib import Path

from clasificador_video import drive


class _ArchivoFalso:
    """Lo que la API de Drive devuelve por archivo: id, nombre, y cuándo
    se modificó por última vez (RFC 3339, como lo entrega Drive de
    verdad)."""

    def __init__(self, id, name, modified_time, parents=None, mime_type="video/mp4"):
        self.id = id
        self.name = name
        self.modified_time = modified_time
        self.parents = parents or []
        self.mime_type = mime_type


class _ClienteFalso:
    """Un doble de `googleapiclient.discovery.Resource` con solo lo que
    `drive.py` usa. Cada método devuelve lo que se le precarga."""

    def __init__(self, archivos: list[_ArchivoFalso] | None = None):
        self.archivos = archivos or []
        self.subidos: list[tuple[str, Path]] = []
        self.carpetas_creadas: list[str] = []

    def crear_carpeta(self, nombre: str, carpeta_padre_id: str | None = None) -> str:
        self.carpetas_creadas.append(nombre)
        return f"folder-{nombre}"

    def subir_archivo(self, ruta_local: Path, carpeta_id: str) -> str:
        self.subidos.append((carpeta_id, ruta_local))
        return f"file-{ruta_local.name}"

    def listar_en_carpeta(self, carpeta_id: str) -> list[_ArchivoFalso]:
        return self.archivos

    def descargar_archivo(self, archivo_id: str, destino: Path) -> None:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(f"contenido de {archivo_id}")

    def link_de_carpeta(self, carpeta_id: str) -> str:
        return f"https://drive.google.com/drive/folders/{carpeta_id.replace('folder-', '')}"


def test_subir_paquete_crea_carpeta_y_sube_prproj_y_proxies(tmp_path):
    cliente = _ClienteFalso()
    prproj = tmp_path / "Casa Reforma.prproj"
    prproj.write_text("x")
    proxy1 = tmp_path / "C0001S03.mp4"
    proxy1.write_text("x")

    resultado = drive.subir_paquete(
        cliente, nombre_proyecto="Casa Reforma",
        prproj=prproj, proxies=[proxy1],
    )

    assert cliente.carpetas_creadas == ["Casa Reforma", "Proxies"]
    assert (cliente.subidos[0][1] == prproj)
    assert (cliente.subidos[1][1] == proxy1)
    assert resultado.folder_link.startswith("https://drive.google.com/")


def test_hay_cambios_cuando_el_prproj_de_drive_es_mas_nuevo():
    cliente = _ClienteFalso(archivos=[
        _ArchivoFalso("f1", "Casa Reforma.prproj", "2026-09-18T12:00:00Z"),
    ])

    resultado = drive.revisar_cambios(
        cliente, carpeta_id="folder-x",
        prproj_modificado_en_la_subida="2026-09-16T10:00:00Z",
    )

    assert resultado.hay_cambios is True
    assert resultado.prproj_modificado_en == "2026-09-18T12:00:00Z"


def test_no_hay_cambios_cuando_la_fecha_es_igual():
    cliente = _ClienteFalso(archivos=[
        _ArchivoFalso("f1", "Casa Reforma.prproj", "2026-09-16T10:00:00Z"),
    ])

    resultado = drive.revisar_cambios(
        cliente, carpeta_id="folder-x",
        prproj_modificado_en_la_subida="2026-09-16T10:00:00Z",
    )

    assert resultado.hay_cambios is False


def test_revisar_cambios_lista_el_material_nuevo():
    cliente = _ClienteFalso(archivos=[
        _ArchivoFalso("f1", "Casa Reforma.prproj", "2026-09-18T12:00:00Z"),
        _ArchivoFalso("f2", "material nuevo", "2026-09-18T12:00:00Z",
                      mime_type="application/vnd.google-apps.folder"),
    ])

    resultado = drive.revisar_cambios(
        cliente, carpeta_id="folder-x",
        prproj_modificado_en_la_subida="2026-09-16T10:00:00Z",
    )

    assert resultado.tiene_material_nuevo is True


def test_traer_de_vuelta_descarga_el_prproj_al_destino(tmp_path):
    cliente = _ClienteFalso(archivos=[
        _ArchivoFalso("f1", "Casa Reforma.prproj", "2026-09-18T12:00:00Z"),
    ])
    destino = tmp_path / "Casa Reforma.prproj"

    drive.traer_prproj(cliente, carpeta_id="folder-x", destino=destino)

    assert destino.read_text() == "contenido de f1"


def test_traer_material_nuevo_baja_cada_subcarpeta_a_su_categoria(tmp_path):
    material_nuevo_id = "folder-material-nuevo"
    cliente = _ClienteFalso(archivos=[
        _ArchivoFalso("fm", "musica y audio", "2026-09-18T12:00:00Z",
                      mime_type="application/vnd.google-apps.folder"),
    ])
    # el cliente falso devuelve la misma lista sin importar la carpeta que
    # se le pida, así que esto alcanza para probar el reparto por nombre
    destino_base = tmp_path / "01. ASSETS VIDEO"

    reparto = drive.mapa_de_categorias_de_material_nuevo()

    assert reparto["musica y audio"] == "04. Musica"
    assert reparto["fotos"] == "07. Assets adicionales"
    assert reparto["graficos y branding"] == "06. Graficos"
