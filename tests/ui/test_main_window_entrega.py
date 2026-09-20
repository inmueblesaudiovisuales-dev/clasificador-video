from pathlib import Path
import json

import pytest
from PySide6.QtWidgets import QMessageBox

from clasificador_video.manifest import Clip
from clasificador_video.rooms import RoomSelection
from clasificador_video.ui.main_window import MainWindow


class FakeMpv:
    def __init__(self, **kwargs):
        self.pause = True
        self.time_pos = 0.0

    def play(self, path):
        pass

    def command(self, *args):
        pass


@pytest.fixture
def ventana(qtbot):
    window = MainWindow(project_name="IAV-2609.10-A", room_selection=RoomSelection(),
                        video_factory=FakeMpv)
    qtbot.addWidget(window)
    return window


def test_al_pedir_subir_llama_a_preguntar_con_los_candidatos(ventana, tmp_path, monkeypatch):
    from clasificador_video import preferencias

    raiz = tmp_path / "IAV"
    (raiz / "2026").mkdir(parents=True)
    (raiz / "2026" / f"{ventana.project_name}.prproj").touch()
    monkeypatch.setattr(preferencias, "carpeta_de_proyectos_premiere", lambda: raiz)
    llamado = {}
    monkeypatch.setattr(
        ventana, "_preguntar_por_el_prproj",
        lambda candidatos: (llamado.setdefault("candidatos", candidatos), None)[1],
    )

    ventana._al_pedir_subir_a_drive()

    assert len(llamado["candidatos"]) == 1


def test_confirmar_traer_de_vuelta_sin_cambios_no_bloquea(ventana, monkeypatch):
    from clasificador_video.drive import ResultadoDeRevision

    monkeypatch.setattr(QMessageBox, "exec", lambda self: None)
    monkeypatch.setattr(QMessageBox, "clickedButton", lambda self: self.buttons()[0])
    resultado = ResultadoDeRevision(
        hay_cambios=False, prproj_modificado_en="x", tiene_material_nuevo=False)

    assert ventana._confirmar_traer_de_vuelta(resultado) is True


def test_el_estado_de_entrega_se_guarda_en_el_proyecto(ventana, tmp_path):
    from clasificador_video.entrega import EstadoEntrega

    ventana._entrega = EstadoEntrega(EstadoEntrega.CON_EDITOR, drive_folder_id="carpeta")

    assert ventana._datos_del_proyecto()["entrega"]["drive_folder_id"] == "carpeta"


def test_revisar_cambios_marca_que_el_editor_contesto(ventana, monkeypatch):
    from clasificador_video import drive
    from clasificador_video.drive import ResultadoDeRevision
    from clasificador_video.entrega import EstadoEntrega

    ventana._entrega = EstadoEntrega(EstadoEntrega.CON_EDITOR, drive_folder_id="carpeta")
    ventana._drive_cliente = object()
    monkeypatch.setattr(
        drive, "revisar_cambios",
        lambda *args: ResultadoDeRevision(True, "nuevo", False),
    )
    monkeypatch.setattr(ventana, "_confirmar_traer_de_vuelta", lambda resultado: False)

    ventana._al_pedir_traer_de_vuelta()

    assert ventana._entrega.estado == EstadoEntrega.EDITOR_CONTESTO


def test_traer_de_vuelta_baja_material_nuevo_desde_la_raiz_del_proyecto(
        ventana, tmp_path, monkeypatch):
    from clasificador_video import drive
    from clasificador_video.entrega import EstadoEntrega

    estado = EstadoEntrega(
        EstadoEntrega.EDITOR_CONTESTO,
        prproj_local=str(tmp_path / "Casa Reforma.prproj"),
        drive_folder_id="folder-x",
    )
    llamado = {}
    monkeypatch.setattr(drive, "traer_prproj", lambda *args: None)
    monkeypatch.setattr(ventana, "_raiz_del_proyecto", lambda: tmp_path)
    monkeypatch.setattr(
        drive, "traer_material_nuevo",
        lambda cliente, carpeta_id, destinos: llamado.update(
            cliente=cliente, carpeta_id=carpeta_id, destinos=destinos),
    )
    monkeypatch.setattr(ventana, "_autosave", lambda: None)

    trabajos = []
    monkeypatch.setattr(ventana._drive_pool, "start", trabajos.append)

    ventana._traer_de_vuelta(estado, object())
    trabajos.pop().run()

    assert llamado["carpeta_id"] == "folder-x"
    assert llamado["destinos"] == {
        "musica y audio": tmp_path / "01. ASSETS VIDEO" / "05. MUSICA Y AUDIO",
        "fotos": tmp_path / "03. ASSETS PHOTOS",
        "graficos y branding": tmp_path / "06. GRAFICOS Y BRANDING",
    }


def test_subir_a_drive_sube_todos_los_clips_con_proxy_sin_importar_el_flag(
    ventana, tmp_path, monkeypatch,
):
    from clasificador_video import drive
    from clasificador_video.drive import ResultadoDeSubida

    proxy_pick = tmp_path / "pick.mp4"
    proxy_reject = tmp_path / "reject.mp4"
    proxy_sin_marcar = tmp_path / "sin_marcar.mp4"
    ventana.clips = [
        Clip(orden=0, ruta=tmp_path / "a.mp4", categoria_path=[], fps=30.0,
             flag="pick", ruta_proxy=proxy_pick),
        Clip(orden=1, ruta=tmp_path / "b.mp4", categoria_path=[], fps=30.0,
             flag="reject", ruta_proxy=proxy_reject),
        Clip(orden=2, ruta=tmp_path / "c.mp4", categoria_path=[], fps=30.0,
             flag="none", ruta_proxy=proxy_sin_marcar),
    ]
    ventana._drive_cliente = object()
    trabajos = []
    llamado = {}
    monkeypatch.setattr(ventana._drive_pool, "start", trabajos.append)
    monkeypatch.setattr(
        drive, "subir_paquete",
        lambda *args, **kwargs: (llamado.update(args=args, kwargs=kwargs),
                                 ResultadoDeSubida("folder-x", "link", "fecha"))[1],
    )
    monkeypatch.setattr(ventana, "_autosave", lambda: None)

    ventana._subir_a_drive(tmp_path / "Casa Reforma.prproj")
    trabajos.pop().run()

    assert set(llamado["args"][3]) == {proxy_pick, proxy_reject, proxy_sin_marcar}


def test_subir_a_drive_manda_los_recursos_locales_que_encuentra(
    ventana, tmp_path, monkeypatch,
):
    """Punto 10 de la tanda del shooting del 2026-09-19: lo que Bruno ya
    trae en sus carpetas de música/fotos/gráficos viaja con el proyecto
    -- spec 2026-09-20-subir-recursos-a-drive-design.md."""
    from clasificador_video import drive
    from clasificador_video.drive import ResultadoDeSubida

    musica_dir = tmp_path / "01. ASSETS VIDEO" / "05. MUSICA Y AUDIO"
    musica_dir.mkdir(parents=True)
    cancion = musica_dir / "cancion.mp3"
    cancion.write_text("x")
    # "fotos" no existe localmente: no debe aparecer en el diccionario.
    monkeypatch.setattr(ventana, "_raiz_del_proyecto", lambda: tmp_path)

    ventana._drive_cliente = object()
    trabajos = []
    llamado = {}
    monkeypatch.setattr(ventana._drive_pool, "start", trabajos.append)
    monkeypatch.setattr(
        drive, "subir_paquete",
        lambda *args, **kwargs: (llamado.update(kwargs=kwargs),
                                 ResultadoDeSubida("folder-x", "link", "fecha"))[1],
    )
    monkeypatch.setattr(ventana, "_autosave", lambda: None)

    ventana._subir_a_drive(tmp_path / "Casa Reforma.prproj")
    trabajos.pop().run()

    assert llamado["kwargs"]["recursos"] == {"musica y audio": [cancion]}


def test_subir_a_drive_sin_raiz_de_proyecto_no_manda_recursos(
    ventana, tmp_path, monkeypatch,
):
    """Sin bins con material todavía no hay raíz de proyecto -- no hay de
    dónde sacar carpetas de recursos, y no debe reventar."""
    from clasificador_video import drive
    from clasificador_video.drive import ResultadoDeSubida

    ventana._drive_cliente = object()
    trabajos = []
    llamado = {}
    monkeypatch.setattr(ventana._drive_pool, "start", trabajos.append)
    monkeypatch.setattr(
        drive, "subir_paquete",
        lambda *args, **kwargs: (llamado.update(kwargs=kwargs),
                                 ResultadoDeSubida("folder-x", "link", "fecha"))[1],
    )
    monkeypatch.setattr(ventana, "_autosave", lambda: None)

    ventana._subir_a_drive(tmp_path / "Casa Reforma.prproj")
    trabajos.pop().run()

    assert llamado["kwargs"]["recursos"] == {}


def test_el_trabajo_de_subida_avisa_el_progreso_a_la_barra(ventana, tmp_path, monkeypatch):
    """La barra decía «Subiendo… 0%» y nunca se movía, aunque el trabajo
    siguiera subiendo archivos. El trabajo le pasa a Drive el aviso de
    progreso y ese aviso termina pintado en el botón."""
    from clasificador_video import drive
    from clasificador_video.drive import ResultadoDeSubida

    ventana._drive_cliente = object()
    trabajos = []
    llamado = {}
    monkeypatch.setattr(ventana._drive_pool, "start", trabajos.append)
    monkeypatch.setattr(
        drive, "subir_paquete",
        lambda *args, **kwargs: (llamado.update(kwargs=kwargs),
                                 ResultadoDeSubida("folder-x", "link", "fecha"))[1],
    )
    monkeypatch.setattr(ventana, "_autosave", lambda: None)

    ventana._subir_a_drive(tmp_path / "Casa Reforma.prproj")
    trabajos.pop().run()
    llamado["kwargs"]["progreso"](42)

    assert "42%" in ventana.title_bar.subir_button.text()
    assert not ventana.title_bar.subir_button.isEnabled()


def test_subir_a_drive_encola_el_trabajo_y_reusa_la_carpeta(ventana, tmp_path, monkeypatch):
    from clasificador_video import drive
    from clasificador_video.drive import ResultadoDeSubida
    from clasificador_video.entrega import EstadoEntrega

    prproj = tmp_path / "Casa Reforma.prproj"
    ventana._entrega = EstadoEntrega(EstadoEntrega.CON_EDITOR, drive_folder_id="folder-viejo")
    ventana._drive_cliente = object()
    trabajos = []
    llamado = {}
    monkeypatch.setattr(ventana._drive_pool, "start", trabajos.append)
    monkeypatch.setattr(
        drive, "subir_paquete",
        lambda *args, **kwargs: (llamado.update(args=args, kwargs=kwargs), ResultadoDeSubida(
            "folder-viejo", "link", "fecha-nueva"))[1],
    )
    monkeypatch.setattr(ventana, "_autosave", lambda: None)

    ventana._subir_a_drive(prproj)
    trabajos.pop().run()

    assert llamado["kwargs"]["carpeta_existente"] == "folder-viejo"
    assert ventana._entrega.drive_prproj_modificado_en == "fecha-nueva"


def test_error_de_subida_rehabilita_el_boton(ventana, monkeypatch):
    avisos = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: avisos.append(args))

    ventana.title_bar.set_subiendo(0)
    ventana._on_drive_subida_lista(None, "red caída")

    assert ventana.title_bar.subir_button.isEnabled()
    assert "Subiendo" not in ventana.title_bar.subir_button.text()


def test_subida_lista_avisa_y_copia_el_enlace_de_la_carpeta(ventana, monkeypatch):
    """Bruno: «al subir a Drive no da el enlace». El link ya se guardaba en
    `self._entrega` -- se veía en el .cvproj -- pero nunca se le enseñaba
    en la ventana, así que no tenía cómo pasárselo al editor por WhatsApp
    o correo, que es justo el paso 4 del flujo de entrega."""
    from clasificador_video.drive import ResultadoDeSubida
    from PySide6.QtWidgets import QApplication

    avisos = []
    monkeypatch.setattr(QMessageBox, "information",
                        lambda self, titulo, texto: avisos.append(texto))
    monkeypatch.setattr(ventana, "_autosave", lambda: None)
    ventana._prproj_subiendo = Path("/tmp/Casa Reforma.prproj")

    resultado = ResultadoDeSubida(
        "folder-x", "https://drive.google.com/drive/folders/folder-x", "fecha")
    ventana._on_drive_subida_lista(resultado, "")

    assert avisos and "https://drive.google.com/drive/folders/folder-x" in avisos[0]
    assert QApplication.clipboard().text() == \
        "https://drive.google.com/drive/folders/folder-x"


def test_cliente_de_drive_reusa_el_token_guardado_sin_ir_a_configuracion(
        ventana, monkeypatch):
    """Antes, una ventana nueva nacía con `_drive_cliente` en `None` y solo
    se llenaba pasando por Configuración -- aunque el permiso ya estuviera
    guardado de una sesión anterior. Bruno lo vivía como «Drive se
    desconecta cada vez que cierro la app»."""
    from clasificador_video import drive

    cliente = object()
    monkeypatch.setattr(drive, "hay_token_guardado", lambda: True)
    monkeypatch.setattr(drive, "cliente_autorizado", lambda ruta: cliente)

    assert ventana._cliente_de_drive() is cliente
    assert ventana._drive_cliente is cliente


def test_cliente_de_drive_sin_token_guardado_sigue_pidiendo_conectar(
        ventana, monkeypatch):
    from clasificador_video import drive

    monkeypatch.setattr(drive, "hay_token_guardado", lambda: False)

    with pytest.raises(RuntimeError):
        ventana._cliente_de_drive()


def test_subir_a_drive_sin_conexion_avisa_en_vez_de_no_hacer_nada(
        ventana, tmp_path, monkeypatch):
    """El bug que Bruno reportó: sin Drive conectado, el botón «Subir» no
    hacía nada visible -- `_cliente_de_drive` ya traía el mensaje correcto,
    pero nadie lo atrapaba para enseñárselo."""
    from clasificador_video import drive

    monkeypatch.setattr(drive, "hay_token_guardado", lambda: False)
    avisos = []
    monkeypatch.setattr(QMessageBox, "warning",
                        lambda self, titulo, texto: avisos.append(texto))
    trabajos = []
    monkeypatch.setattr(ventana._drive_pool, "start", trabajos.append)

    ventana._subir_a_drive(tmp_path / "Casa Reforma.prproj")

    assert avisos == ["Conecta Google Drive desde Configuración antes de subir."]
    assert trabajos == []
    assert avisos


def test_error_de_traida_muestra_un_aviso(ventana, monkeypatch):
    avisos = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: avisos.append(args))

    ventana._on_drive_traida_lista("No se encontró ningún .prproj en la carpeta de Drive.")

    assert avisos


def test_traer_de_vuelta_deja_el_proyecto_en_revision(ventana, tmp_path, monkeypatch):
    from clasificador_video.entrega import EstadoEntrega

    ventana._entrega = EstadoEntrega(
        EstadoEntrega.CON_EDITOR,
        prproj_local=str(tmp_path / "Casa Reforma.prproj"),
        drive_folder_id="folder-x",
    )
    monkeypatch.setattr(ventana, "_autosave", lambda: None)

    ventana._on_drive_traida_lista("")

    assert ventana._entrega.estado == EstadoEntrega.EN_REVISION
    assert ventana._entrega.drive_folder_id == "folder-x"
    assert "En revisión" in ventana.title_bar.entrega_pill.text()


def test_refrescar_actualiza_el_cvproj_cuando_hay_cambios(ventana, tmp_path, monkeypatch):
    from clasificador_video import drive
    from clasificador_video.entrega import EstadoEntrega

    ruta = tmp_path / "Casa Reforma.cvproj"
    data = {"entrega": EstadoEntrega(
        estado=EstadoEntrega.CON_EDITOR, drive_folder_id="folder-x",
        drive_prproj_modificado_en="2026-09-16T10:00:00Z",
    ).to_dict()}
    ruta.write_text(json.dumps(data))

    cliente = object()

    def persistir(ruta_recibida, cliente_recibido):
        assert ruta_recibida == ruta
        assert cliente_recibido is cliente
        guardado = json.loads(ruta.read_text())
        guardado["entrega"]["estado"] = EstadoEntrega.EDITOR_CONTESTO
        ruta.write_text(json.dumps(guardado))
        return True

    monkeypatch.setattr(ventana, "_cliente_de_drive", lambda: cliente)
    monkeypatch.setattr(drive, "revisar_y_persistir", persistir)

    ventana._al_refrescar_entrega(ruta)

    guardado = json.loads(ruta.read_text())
    assert guardado["entrega"]["estado"] == EstadoEntrega.EDITOR_CONTESTO
