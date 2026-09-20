# tests/test_drive.py
import json
from pathlib import Path

import pytest

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
        self.coloreadas: list[tuple[str, str]] = []
        self._archivos_por_carpeta: dict[str, list[_ArchivoFalso]] = {}

    def crear_carpeta(self, nombre: str, carpeta_padre_id: str | None = None) -> str:
        self.carpetas_creadas.append(nombre)
        carpeta_id = f"folder-{nombre}"
        if carpeta_padre_id is not None:
            self._archivos_por_carpeta.setdefault(carpeta_padre_id, []).append(
                _ArchivoFalso(carpeta_id, nombre, "2026-09-19T12:00:00Z",
                              mime_type=drive.CARPETA_MIME))
        self._archivos_por_carpeta.setdefault(carpeta_id, [])
        return carpeta_id

    def subir_archivo(self, ruta_local: Path, carpeta_id: str) -> str:
        self.subidos.append((carpeta_id, ruta_local))
        archivo_id = f"file-{ruta_local.name}"
        self._archivos_por_carpeta.setdefault(carpeta_id, []).append(
            _ArchivoFalso(archivo_id, ruta_local.name, "2026-09-19T12:00:00Z"))
        return archivo_id

    def listar_en_carpeta(self, carpeta_id: str) -> list[_ArchivoFalso]:
        return self._archivos_por_carpeta.get(carpeta_id, self.archivos)

    def descargar_archivo(self, archivo_id: str, destino: Path) -> None:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(f"contenido de {archivo_id}")

    def link_de_carpeta(self, carpeta_id: str) -> str:
        return f"https://drive.google.com/drive/folders/{carpeta_id.replace('folder-', '')}"

    def colorear_carpeta(self, carpeta_id: str, color: str) -> None:
        self.coloreadas.append((carpeta_id, color))


class _ClientePorCarpeta(_ClienteFalso):
    """Doble que imita las listas distintas de cada carpeta de Drive."""

    def __init__(self, archivos_por_carpeta: dict[str, list[_ArchivoFalso]]):
        super().__init__()
        self.archivos_por_carpeta = archivos_por_carpeta

    def listar_en_carpeta(self, carpeta_id: str) -> list[_ArchivoFalso]:
        return self.archivos_por_carpeta.get(carpeta_id, [])


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

    assert cliente.carpetas_creadas == [
        "Proyectos para edición externa", "Casa Reforma", "Proxies"]
    assert (cliente.subidos[0][1] == prproj)
    assert (cliente.subidos[1][1] == proxy1)
    assert resultado.folder_link.startswith("https://drive.google.com/")


def test_subir_paquete_crea_la_carpeta_del_proyecto_dentro_de_entregas(tmp_path):
    cliente = _ClienteFalso()
    prproj = tmp_path / "Casa Reforma.prproj"
    prproj.write_text("x")

    drive.subir_paquete(cliente, "Casa Reforma", prproj, [])

    entregas_id = "folder-Proyectos para edición externa"
    hijos = cliente.listar_en_carpeta(entregas_id)
    assert any(h.name == "Casa Reforma" for h in hijos)


def test_subir_paquete_reusa_la_carpeta_de_entregas_si_ya_existe(tmp_path):
    cliente = _ClienteFalso()
    cliente.crear_carpeta("Proyectos para edición externa", carpeta_padre_id="root")
    cliente.carpetas_creadas.clear()
    prproj = tmp_path / "Casa Reforma.prproj"
    prproj.write_text("x")

    drive.subir_paquete(cliente, "Casa Reforma", prproj, [])

    assert "Proyectos para edición externa" not in cliente.carpetas_creadas
    assert cliente.carpetas_creadas == ["Casa Reforma", "Proxies"]


def test_subir_paquete_avisa_el_progreso_por_archivo(tmp_path):
    """El botón decía «Subiendo… 0%» y ahí se quedaba hasta terminar: con
    214 proxies eso se lee como app trabada, aunque Drive sí esté
    recibiendo. El avance se cuenta por archivo subido."""
    cliente = _ClienteFalso()
    prproj = tmp_path / "Casa Reforma.prproj"
    prproj.write_text("x")
    proxy1 = tmp_path / "C0001S03.mp4"
    proxy1.write_text("x")
    proxy2 = tmp_path / "C0002S03.mp4"
    proxy2.write_text("x")
    avances = []

    drive.subir_paquete(
        cliente, "Casa Reforma", prproj, [proxy1, proxy2], progreso=avances.append)

    assert avances == [33, 67, 100]


def test_subir_paquete_sin_progreso_no_falla(tmp_path):
    cliente = _ClienteFalso()
    prproj = tmp_path / "Casa Reforma.prproj"
    prproj.write_text("x")

    resultado = drive.subir_paquete(cliente, "Casa Reforma", prproj, [])

    assert resultado.folder_id == "folder-Casa Reforma"


def test_subir_paquete_colorea_la_carpeta_de_rojo(tmp_path):
    cliente = _ClienteFalso()
    prproj = tmp_path / "Casa Reforma.prproj"
    prproj.write_text("x")

    resultado = drive.subir_paquete(cliente, "Casa Reforma", prproj, [])

    assert cliente.coloreadas == [(resultado.folder_id, drive.COLOR_FALTA_EDITAR)]


def test_subir_de_nuevo_tambien_colorea_de_rojo(tmp_path):
    cliente = _ClienteFalso()
    prproj = tmp_path / "Casa Reforma.prproj"
    prproj.write_text("x")

    drive.subir_paquete(cliente, "Casa Reforma", prproj, [], carpeta_existente="folder-x")

    assert cliente.coloreadas == [("folder-x", drive.COLOR_FALTA_EDITAR)]


def test_subir_paquete_devuelve_la_fecha_del_prproj_subido(tmp_path):
    cliente = _ClienteFalso()
    prproj = tmp_path / "Casa Reforma.prproj"
    prproj.write_text("x")

    resultado = drive.subir_paquete(cliente, "Casa Reforma", prproj, [])

    assert resultado.prproj_modificado_en == "2026-09-19T12:00:00Z"


def test_subir_de_nuevo_reusa_la_carpeta_existente(tmp_path):
    cliente = _ClienteFalso()
    prproj = tmp_path / "Casa Reforma.prproj"
    prproj.write_text("x")

    resultado = drive.subir_paquete(
        cliente, "Casa Reforma", prproj, [], carpeta_existente="folder-x")

    assert resultado.folder_id == "folder-x"
    assert "Casa Reforma" not in cliente.carpetas_creadas


def test_subir_de_nuevo_reusa_la_subcarpeta_de_proxies_si_ya_existe(tmp_path):
    cliente = _ClienteFalso()
    cliente.crear_carpeta("Proxies", carpeta_padre_id="folder-x")
    cliente.carpetas_creadas.clear()
    prproj = tmp_path / "Casa Reforma.prproj"
    prproj.write_text("x")

    drive.subir_paquete(cliente, "Casa Reforma", prproj, [], carpeta_existente="folder-x")

    assert cliente.carpetas_creadas == []


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


def test_traer_prproj_sin_prproj_da_un_error_claro(tmp_path):
    cliente = _ClienteFalso(archivos=[
        _ArchivoFalso("f1", "notas.txt", "2026-09-18T12:00:00Z"),
    ])

    with pytest.raises(RuntimeError, match="No se encontró ningún .prproj en la carpeta de Drive."):
        drive.traer_prproj(cliente, carpeta_id="folder-x", destino=tmp_path / "Casa.prproj")


def test_material_nuevo_se_reparte_a_las_rutas_reales_del_proyecto():
    reparto = drive.mapa_de_categorias_de_material_nuevo()

    assert reparto["musica y audio"] == "01. ASSETS VIDEO/05. MUSICA Y AUDIO"
    assert reparto["fotos"] == "03. ASSETS PHOTOS"
    assert reparto["graficos y branding"] == "06. GRAFICOS Y BRANDING"


def test_traer_material_nuevo_baja_archivos_y_no_crea_categorias_vacias(tmp_path):
    cliente = _ClientePorCarpeta({
        "proyecto": [
            _ArchivoFalso("nuevo", "material nuevo", "2026-09-18T12:00:00Z",
                          mime_type=drive.CARPETA_MIME),
        ],
        "nuevo": [
            _ArchivoFalso("musica", "musica y audio", "2026-09-18T12:00:00Z",
                          mime_type=drive.CARPETA_MIME),
            _ArchivoFalso("fotos", "fotos", "2026-09-18T12:00:00Z",
                          mime_type=drive.CARPETA_MIME),
        ],
        "musica": [
            _ArchivoFalso("audio", "cortinilla.mp3", "2026-09-18T12:00:00Z"),
        ],
        "fotos": [],
    })
    destino_audio = tmp_path / "01. ASSETS VIDEO" / "05. MUSICA Y AUDIO"
    destino_fotos = tmp_path / "03. ASSETS PHOTOS"

    bajadas = drive.traer_material_nuevo(
        cliente, "proyecto", {
            "musica y audio": destino_audio,
            "fotos": destino_fotos,
        },
    )

    assert bajadas == ["musica y audio"]
    assert (destino_audio / "cortinilla.mp3").read_text() == "contenido de audio"
    assert not destino_fotos.exists()


def test_traer_material_nuevo_sin_la_carpeta_devuelve_lista_vacia(tmp_path):
    cliente = _ClientePorCarpeta({"proyecto": []})

    bajadas = drive.traer_material_nuevo(
        cliente, "proyecto", {"fotos": tmp_path / "03. ASSETS PHOTOS"},
    )

    assert bajadas == []


def test_revisar_y_persistir_marca_al_editor_cuando_drive_tiene_cambios(tmp_path):
    from clasificador_video.entrega import EstadoEntrega

    ruta = tmp_path / "Casa Reforma.cvproj"
    ruta.write_text(json.dumps({"entrega": EstadoEntrega(
        EstadoEntrega.CON_EDITOR,
        drive_folder_id="folder-x",
        drive_prproj_modificado_en="2026-09-16T10:00:00Z",
    ).to_dict()}))
    cliente = _ClienteFalso([
        _ArchivoFalso("prproj", "Casa Reforma.prproj", "2026-09-18T12:00:00Z"),
    ])

    resultado = drive.revisar_y_persistir(ruta, cliente)

    assert resultado.hay_cambios is True
    assert json.loads(ruta.read_text())["entrega"]["estado"] == EstadoEntrega.EDITOR_CONTESTO
    assert cliente.coloreadas == [("folder-x", drive.COLOR_YA_REGRESO)]


def test_revisar_y_persistir_sin_cambios_no_toca_el_color(tmp_path):
    from clasificador_video.entrega import EstadoEntrega

    ruta = tmp_path / "Casa Reforma.cvproj"
    ruta.write_text(json.dumps({"entrega": EstadoEntrega(
        EstadoEntrega.CON_EDITOR,
        drive_folder_id="folder-x",
        drive_prproj_modificado_en="2026-09-16T10:00:00Z",
    ).to_dict()}))
    cliente = _ClienteFalso([
        _ArchivoFalso("prproj", "Casa Reforma.prproj", "2026-09-16T10:00:00Z"),
    ])

    resultado = drive.revisar_y_persistir(ruta, cliente)

    assert resultado.hay_cambios is False
    assert cliente.coloreadas == []


def test_revisar_y_persistir_sin_cambios_no_toca_el_proyecto(tmp_path):
    from clasificador_video.entrega import EstadoEntrega

    ruta = tmp_path / "Casa Reforma.cvproj"
    data = {"entrega": EstadoEntrega(
        EstadoEntrega.CON_EDITOR,
        drive_folder_id="folder-x",
        drive_prproj_modificado_en="2026-09-16T10:00:00Z",
    ).to_dict()}
    ruta.write_text(json.dumps(data))
    antes = ruta.read_text()
    cliente = _ClienteFalso([
        _ArchivoFalso("prproj", "Casa Reforma.prproj", "2026-09-16T10:00:00Z"),
    ])

    drive.revisar_y_persistir(ruta, cliente)

    assert ruta.read_text() == antes


def test_revisar_y_persistir_sin_entrega_devuelve_none(tmp_path):
    ruta = tmp_path / "Casa Reforma.cvproj"
    ruta.write_text(json.dumps({"proyecto": "Casa Reforma"}))

    resultado = drive.revisar_y_persistir(ruta, _ClienteFalso())

    assert resultado is None


def test_mensaje_confirmar_traida_con_cambios_en_el_prproj():
    resultado = drive.ResultadoDeRevision(
        hay_cambios=True, prproj_modificado_en="x", tiene_material_nuevo=False)

    mensaje = drive.mensaje_confirmar_traida(resultado)

    assert mensaje.texto == "Se encontró algo nuevo en Drive."
    assert "El .prproj cambió." in mensaje.informativo
    assert "material nuevo" not in mensaje.informativo
    assert mensaje.texto_boton == "Traer de vuelta"


def test_mensaje_confirmar_traida_con_material_nuevo():
    resultado = drive.ResultadoDeRevision(
        hay_cambios=False, prproj_modificado_en="x", tiene_material_nuevo=True)

    mensaje = drive.mensaje_confirmar_traida(resultado)

    assert "El .prproj no ha cambiado." in mensaje.informativo
    assert 'Hay contenido en "material nuevo/".' in mensaje.informativo
    assert mensaje.texto_boton == "Traer de vuelta"


def test_mensaje_confirmar_traida_sin_nada_nuevo():
    resultado = drive.ResultadoDeRevision(
        hay_cambios=False, prproj_modificado_en="x", tiene_material_nuevo=False)

    mensaje = drive.mensaje_confirmar_traida(resultado)

    assert mensaje.texto == (
        "No parece que el editor haya subido nada todavía. "
        "¿Seguro que quieres continuar?"
    )
    assert mensaje.texto_boton == "Traer de todas formas"
