# tests/test_app.py
#
# Este archivo estuvo EXCLUIDO de la corrida durante meses por un cuelgue
# bajo `offscreen`. **Ya no cuelga**: la F3 lo reescribió —el diálogo de
# configuración de cuartos, que abría con `exec()` y bloqueaba, murió con
# ella— y desde entonces corre en medio segundo. Comprobado con cinco
# corridas de la suite completa el 2026-08-08.
#
#     QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
#
# Si alguna vez vuelve a colgarse, es un bug a resolver, no una limitación a
# esquivar. Cubre el arranque de la app, que ningún otro test toca.
import json
from pathlib import Path

from PySide6.QtWidgets import QFileDialog

from clasificador_video import app as app_module
from clasificador_video.app import (
    Coordinador,
    abrir_proyecto,
    arrancar_inicio,
    crear_proyecto,
    migrar_sesion,
    migrar_sesion_vieja,
)
from clasificador_video.proyecto import abrir, guardar
from clasificador_video.ui import theme


class _FakeMpv:
    """Evita abrir un mpv real en pruebas que no verifican video.

    MpvPlayer crea el reproductor en el constructor (ya no al mostrarse el
    widget), y VideoWidget.player lo crea perezosamente al primer acceso.
    Abrir un proyecto con clips abre el primero -- sin este doble, cada
    prueba de app.py abriria un mpv real y su hilo de eventos, acumulando
    hilos reales entre pruebas hasta comprometer el proceso (crash nativo
    documentado en el handoff).
    """

    def __init__(self, **kwargs):
        self.init_kwargs = kwargs
        self.pause = True
        self.time_pos = 0.0
        self.loaded_path = None

    def play(self, path):
        self.loaded_path = path

    def command(self, *args):
        pass


def _clip_crudo(ruta="/cam/C0001.MP4", categoria_path=None, flag="none"):
    return {
        "orden": 1, "ruta": ruta, "fps": 30.0,
        "categoria_path": categoria_path if categoria_path is not None else [],
        "in_frame": None, "out_frame": None, "flag": flag, "ruta_proxy": None,
    }


def _documento(extra=None):
    data = {
        "version": 1,
        "proyecto": "P",
        "rooms": ["Sala"],
        "clips": [_clip_crudo(categoria_path=["Sala"], flag="pick")],
        "bins": [{"nombre": "Sony", "origen": "/cam", "clips": [0]}],
        "tamanos": {}, "duraciones": {}, "rotaciones": {},
        "relativas": {"0": "C0001.MP4"}, "bytes": {},
    }
    data.update(extra or {})
    return data


def _proyecto_en(tmp_path, extra=None, nombre="P.cvproj"):
    ruta = tmp_path / nombre
    guardar(ruta, _documento(extra))
    return ruta


def _sesion_vieja(tmp_path, extra=None):
    """La sesión escondida de antes de que los proyectos tuvieran nombre."""
    sesion = tmp_path / "sesion.json"
    data = {
        "proyecto": "Lo de antes", "rooms": ["Cocina"],
        "clips": [_clip_crudo(categoria_path=["Cocina"], flag="pick")],
        "bins": [], "tamanos": {}, "duraciones": {}, "rotaciones": {},
    }
    data.update(extra or {})
    sesion.write_text(json.dumps(data))
    return sesion


# --- sesiones viejas: lo que se conserva de ellas ---------------------------


def test_una_sesion_vieja_con_subcuartos_se_aplana_al_cuarto_padre():
    """Se conserva el cuarto, que sigue existiendo; se descarta el subcuarto,
    que ya no es representable. Tirar el clip entero seria peor: el editor ya
    tomo esa decision."""
    clip = app_module._clip_from_dict({
        "orden": 1, "ruta": "/x.MP4", "fps": 30.0,
        "categoria_path": ["Recámara 1", "Baño"],
    })
    assert clip.categoria_path == ["Recámara 1"]


def test_el_dialogo_de_configuracion_ya_no_existe():
    assert not hasattr(app_module, "RoomConfigDialog")


# --- abrir un proyecto -----------------------------------------------------


def test_arranca_mostrando_los_recientes(qtbot, tmp_path):
    inicio = arrancar_inicio(recientes_path=tmp_path / "r.json")
    qtbot.addWidget(inicio)

    assert inicio.nombres_visibles() == []


def test_abrir_un_proyecto_carga_sus_clips_y_sus_bins(qtbot, tmp_path):
    ruta = _proyecto_en(tmp_path)

    window = abrir_proyecto(ruta, video_factory=_FakeMpv,
                            recientes_path=tmp_path / "r.json")
    qtbot.addWidget(window)

    assert window.project_name == "P"
    assert [c.ruta for c in window.clips] == [Path("/cam/C0001.MP4")]
    assert window.bins.nombres() == ["Sony"]
    assert window.clips[0].flag == "pick"
    assert window.room_selection.active_rooms() == ["Sala"]


def test_abrir_un_proyecto_devuelve_los_tamanos_antes_de_las_miniaturas(qtbot, tmp_path):
    """Sin esto el material vertical se dibujaba en tarjetas horizontales:
    no habia con que calcular el aspecto. Y la duracion decide si se extrae
    la tira de 12 cuadros o un solo frame, asi que va ANTES de programarlas.

    Las miniaturas ahora se programan cuando termina la revision de media
    --que corre en otro hilo-- para no pedirle la portada a archivos que no
    existen, asi que hay que esperarla."""
    ruta = _proyecto_en(tmp_path, {
        "tamanos": {"0": [2160, 3840]},
        "duraciones": {"0": 18.4},
        "rotaciones": {"0": 90},
    })

    window = abrir_proyecto(ruta, video_factory=_FakeMpv,
                            recientes_path=tmp_path / "r.json")
    qtbot.addWidget(window)

    assert window._clip_sizes == {0: (2160, 3840)}
    assert window._clip_durations == {0: 18.4}
    assert window._clip_rotations == {0: 90}
    assert window.aspect_ratio_for(0) == 2160 / 3840
    qtbot.waitUntil(lambda: window._thumb_generation == 1, timeout=3000)


def test_abrir_un_proyecto_trae_lo_que_sirve_para_reencontrar(qtbot, tmp_path):
    ruta = _proyecto_en(tmp_path, {"bytes": {"0": 700}})

    window = abrir_proyecto(ruta, video_factory=_FakeMpv,
                            recientes_path=tmp_path / "r.json")
    qtbot.addWidget(window)

    assert window._relativas == {0: "C0001.MP4"}
    assert window._bytes_guardados == {0: 700}


def test_abrir_un_proyecto_con_la_media_perdida_lo_avisa_de_una(qtbot, tmp_path):
    """Abrirlo en otra computadora quiere decir que NINGUNA ruta coincide.
    Es el caso normal, no la excepción, así que se dice al abrir y no
    cuando Bruno hace clic en un clip y no pasa nada."""
    ruta = _proyecto_en(tmp_path)

    window = abrir_proyecto(ruta, video_factory=_FakeMpv,
                            recientes_path=tmp_path / "r.json")
    qtbot.addWidget(window)

    # el barrido corre fuera del hilo de la interfaz: son `stat` uno por
    # clip en serie, y el material puede colgar de un disco de red que ya no
    # responde. Justo al abrir es el peor momento para congelar la ventana.
    qtbot.waitUntil(lambda: not window.aviso_de_media.isHidden(), timeout=3000)
    assert window.aviso_de_media.text() == "Sony — 1 clip no se encuentra."


def test_un_proyecto_viejo_sin_bins_cae_en_uno_solo(qtbot, tmp_path):
    """Un documento de antes de que existieran los bins no trae la llave.
    No se pierde: todo el material cae en un bin unico."""
    ruta = _proyecto_en(tmp_path, {"bins": None})

    window = abrir_proyecto(ruta, video_factory=_FakeMpv,
                            recientes_path=tmp_path / "r.json")
    qtbot.addWidget(window)

    assert window.bins.nombres() == ["cam"]
    assert window.bins.clips_de("cam") == [0]


def test_abrir_guarda_en_el_archivo_que_bruno_eligio(qtbot, tmp_path):
    """El autoguardado no cambia: escribe donde diga `session_path`, y eso
    ahora apunta al .cvproj."""
    ruta = _proyecto_en(tmp_path)

    window = abrir_proyecto(ruta, video_factory=_FakeMpv,
                            recientes_path=tmp_path / "r.json")
    qtbot.addWidget(window)

    assert window.session_path == ruta


def test_abrir_lo_registra_en_recientes(qtbot, tmp_path):
    from clasificador_video.recientes import Recientes

    ruta = _proyecto_en(tmp_path)
    recientes = tmp_path / "r.json"

    window = abrir_proyecto(ruta, video_factory=_FakeMpv, recientes_path=recientes)
    qtbot.addWidget(window)

    assert [(e.nombre, e.ruta) for e in Recientes(recientes).lista()] == [("P", ruta)]


def test_abrir_algo_ilegible_no_revienta(tmp_path):
    malo = tmp_path / "roto.cvproj"
    malo.write_text("esto no es json {")

    assert abrir_proyecto(malo, video_factory=_FakeMpv,
                          recientes_path=tmp_path / "r.json") is None


def test_un_json_cualquiera_no_abre_un_proyecto_vacio(qtbot, tmp_path):
    """`proyecto.abrir` acepta cualquier JSON que sea un objeto, asi que con
    «Abrir otro…» se puede elegir un `.json` de otra cosa. Abrirlo como un
    proyecto vacio seria peor que no abrirlo: Bruno veria una ventana en
    blanco y creeria que perdio el trabajo."""
    otro = tmp_path / "config.json"
    otro.write_text(json.dumps({"tema": "oscuro", "volumen": 0.8}))

    assert abrir_proyecto(otro, video_factory=_FakeMpv,
                          recientes_path=tmp_path / "r.json") is None


def test_un_proyecto_sin_version_pero_con_clips_si_abre(qtbot, tmp_path):
    """Los .cvproj migrados de la sesion vieja pueden no traer version. Con
    clips adentro es un proyecto, y exigir las dos cosas dejaria a Bruno sin
    poder abrir lo suyo."""
    ruta = tmp_path / "viejo.cvproj"
    ruta.write_text(json.dumps({"proyecto": "P", "clips": [_clip_crudo()]}))

    window = abrir_proyecto(ruta, video_factory=_FakeMpv,
                            recientes_path=tmp_path / "r.json")
    qtbot.addWidget(window)

    assert window is not None


def test_un_proyecto_con_clips_rotos_no_tira_la_app(qtbot, tmp_path):
    """`es_proyecto` solo mira que la llave exista, asi que cualquier JSON
    con `clips` pasa. Si el armado del clip truena, truena DENTRO de un slot
    de Qt --el clic en la fila-- y una excepcion sin atrapar ahi aborta el
    proceso: la app se cierra sola. Alcanzable desde «Abrir otro…» y desde
    una sesion migrada a medio corromper.
    """
    for clips in ([{"orden": 1}],                       # sin ruta ni fps
                  [{"ruta": "/a.MP4", "fps": 30.0}],    # sin orden
                  ["esto no es un clip"],
                  [{"orden": 1, "ruta": "/a.MP4", "fps": "treinta"}]):
        ruta = tmp_path / "roto.cvproj"
        guardar(ruta, {"version": 1, "proyecto": "P", "clips": clips})

        assert abrir_proyecto(ruta, video_factory=_FakeMpv,
                              recientes_path=tmp_path / "r.json") is None


def test_un_proyecto_con_clips_rotos_lo_dice_en_la_pantalla(qtbot, tmp_path):
    coord = _coordinador(tmp_path)
    qtbot.addWidget(coord.inicio)
    coord.mostrar_inicio()
    ruta = tmp_path / "roto.cvproj"
    guardar(ruta, {"version": 1, "proyecto": "P", "clips": [{"orden": 1}]})

    coord.inicio.abrir_pedido.emit(ruta)

    assert coord.ventanas == []
    assert coord.inicio.aviso.isVisible()


def test_abrir_sin_la_media_no_borra_los_pesos_al_autoguardar(qtbot, tmp_path):
    """EL pendiente de este plan, de punta a punta.

    Guardas con la media conectada, abres el .cvproj en otra computadora, y
    el autoguardado se dispara solo a los pocos segundos --lo dispara
    `load_clips`--. Si ahi se reescriben los pesos «como se ven», el archivo
    queda sin ninguno, porque no hay nada que medir. Y recien entonces Bruno
    aprieta «Buscar…», ya sin con que confirmar que un archivo es el que era.
    """
    ruta = _proyecto_en(tmp_path, {
        "clips": [_clip_crudo(ruta="/tarjeta/que/no/esta/C0001.MP4")],
        "bins": [{"nombre": "Sony", "origen": "/tarjeta/que/no/esta",
                  "clips": [0]}],
        "bytes": {"0": 700},
    })

    window = abrir_proyecto(ruta, video_factory=_FakeMpv,
                            recientes_path=tmp_path / "r.json")
    qtbot.addWidget(window)

    # el autoguardado quedo armado solo, sin que nadie tocara una tecla
    assert window._autosave_timer.isActive()
    qtbot.wait(500)                       # se cumple el debounce y escribe
    window._autosave_pool.waitForDone(2000)

    assert abrir(ruta)["bytes"] == {"0": 700}
    assert abrir(ruta)["relativas"] == {"0": "C0001.MP4"}


# --- proyecto nuevo --------------------------------------------------------


def test_proyecto_nuevo_crea_el_archivo_de_una_vez(qtbot, tmp_path):
    """Nunca existe trabajo sin un archivo donde vivir: decision de Bruno."""
    ruta = tmp_path / "Casa Nueva.cvproj"

    window = crear_proyecto(ruta, "Casa Nueva", video_factory=_FakeMpv,
                            recientes_path=tmp_path / "r.json")
    qtbot.addWidget(window)

    assert ruta.exists()
    assert window.project_name == "Casa Nueva"
    assert window.clips == []
    assert abrir(ruta)["proyecto"] == "Casa Nueva"


def test_proyecto_nuevo_queda_en_recientes(qtbot, tmp_path):
    from clasificador_video.recientes import Recientes

    recientes = tmp_path / "r.json"
    window = crear_proyecto(tmp_path / "Casa Nueva.cvproj", "Casa Nueva",
                            video_factory=_FakeMpv, recientes_path=recientes)
    qtbot.addWidget(window)

    assert [e.nombre for e in Recientes(recientes).lista()] == ["Casa Nueva"]


# --- migrar la sesion vieja ------------------------------------------------


def test_la_sesion_vieja_se_convierte_en_proyecto(tmp_path):
    """Bruno tiene material clasificado en la sesion escondida. Al arrancar
    con esto por primera vez, NO se pierde."""
    sesion = _sesion_vieja(tmp_path)
    destino = tmp_path / "convertido.cvproj"

    assert migrar_sesion(sesion, destino) is True

    data = abrir(destino)
    assert data["proyecto"] == "Lo de antes"
    assert data["clips"][0]["flag"] == "pick"
    assert data["version"] == 1
    # la vieja NO se borra: se conserva hasta que lo nuevo este a salvo
    assert sesion.exists()


def test_una_sesion_sin_clips_no_se_migra(tmp_path):
    sesion = _sesion_vieja(tmp_path, {"clips": []})

    assert migrar_sesion(sesion, tmp_path / "x.cvproj") is False
    assert not (tmp_path / "x.cvproj").exists()


def test_migrar_una_sesion_que_no_esta_no_revienta(tmp_path):
    assert migrar_sesion(tmp_path / "no-esta.json", tmp_path / "x.cvproj") is False


def test_la_sesion_migrada_queda_en_recientes(tmp_path):
    from clasificador_video.recientes import Recientes

    sesion = _sesion_vieja(tmp_path)
    recientes = tmp_path / "r.json"

    destino = migrar_sesion_vieja(sesion=sesion, carpeta=tmp_path / "docs",
                                  recientes_path=recientes)

    assert destino == tmp_path / "docs" / "Lo de antes.cvproj"
    assert [e.nombre for e in Recientes(recientes).lista()] == ["Lo de antes"]


def test_la_sesion_vieja_se_migra_una_sola_vez(tmp_path):
    """Si se migrara en cada arranque, el trabajo de hoy se pisaria con el
    de la sesion vieja cada vez que Bruno abre la app."""
    sesion = _sesion_vieja(tmp_path)
    recientes = tmp_path / "r.json"

    primero = migrar_sesion_vieja(sesion=sesion, carpeta=tmp_path / "docs",
                                  recientes_path=recientes)
    segundo = migrar_sesion_vieja(sesion=sesion, carpeta=tmp_path / "docs",
                                  recientes_path=recientes)

    assert primero is not None
    assert segundo is None


def test_migrar_conserva_la_sesion_vieja_con_todo_adentro(tmp_path):
    """Se conserva hasta que lo nuevo este a salvo: borrar lo viejo antes de
    que lo nuevo exista es como se pierden cosas. Se aparta con otro nombre,
    que ademas es la marca de que ya se migro."""
    sesion = _sesion_vieja(tmp_path)
    antes = sesion.read_text()

    migrar_sesion_vieja(sesion=sesion, carpeta=tmp_path / "docs",
                        recientes_path=tmp_path / "r.json")

    apartada = tmp_path / "sesion.migrada.json"
    assert apartada.exists()
    assert apartada.read_text() == antes


def test_sin_sesion_vieja_no_hay_nada_que_migrar(tmp_path):
    assert migrar_sesion_vieja(sesion=tmp_path / "no-esta.json",
                               carpeta=tmp_path / "docs",
                               recientes_path=tmp_path / "r.json") is None


def test_migrar_no_pisa_un_proyecto_que_ya_estaba_ahi(tmp_path):
    """Dos migraciones distintas con el mismo nombre de proyecto no se
    sobreescriben: la segunda busca otro nombre."""
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "Lo de antes.cvproj").write_text("{}")
    sesion = _sesion_vieja(tmp_path)

    destino = migrar_sesion_vieja(sesion=sesion, carpeta=docs,
                                  recientes_path=tmp_path / "r.json")

    assert destino == docs / "Lo de antes (2).cvproj"
    assert (docs / "Lo de antes.cvproj").read_text() == "{}"


# --- el coordinador: los tres caminos de la pantalla de inicio -------------


def _coordinador(tmp_path):
    return Coordinador(recientes_path=tmp_path / "r.json", video_factory=_FakeMpv)


def test_abrir_desde_la_pantalla_esconde_la_pantalla(qtbot, tmp_path):
    coord = _coordinador(tmp_path)
    qtbot.addWidget(coord.inicio)
    ruta = _proyecto_en(tmp_path)
    coord.mostrar_inicio()

    coord.inicio.abrir_pedido.emit(ruta)

    assert len(coord.ventanas) == 1
    assert not coord.inicio.isVisible()
    coord.ventanas[0].close()


def test_abrir_desde_la_pantalla_no_pierde_el_proxy(qtbot, tmp_path):
    """El clip donde aterrizas al abrir un proyecto tiene que abrirse por su
    PROXY, como cualquier otro.

    Abrirlo otra vez «por si acaso» lo abre con la ruta en crudo y borra en
    silencio una fase entera de trabajo: un cuadro atras pasa de 22 ms a
    530 ms justo en el clip donde caes cada vez que abres el proyecto, y no
    hay ninguna señal de por que.
    """
    proxy = tmp_path / "C0001S03.MP4"
    proxy.write_bytes(b"x")
    ruta = _proyecto_en(tmp_path, {
        "clips": [dict(_clip_crudo(), ruta_proxy=str(proxy))],
    })
    coord = _coordinador(tmp_path)
    qtbot.addWidget(coord.inicio)
    coord.mostrar_inicio()

    coord.inicio.abrir_pedido.emit(ruta)

    ventana = coord.ventanas[0]
    assert ventana.video_widget.player._mpv.loaded_path == str(proxy)
    ventana.close()


def test_al_cerrarse_la_ventana_vuelve_la_pantalla(qtbot, tmp_path):
    coord = _coordinador(tmp_path)
    qtbot.addWidget(coord.inicio)
    coord.mostrar_inicio()
    coord.inicio.abrir_pedido.emit(_proyecto_en(tmp_path))
    ventana = coord.ventanas[0]

    ventana.close()

    assert coord.ventanas == []
    assert coord.inicio.isVisible()
    # y con la lista al dia: el proyecto que se acaba de cerrar esta arriba
    assert coord.inicio.nombres_visibles() == ["P"]


def test_un_proyecto_que_no_abre_deja_la_pantalla_puesta(qtbot, tmp_path):
    """Y lo dice EN la pantalla, en vez de dejar a Bruno mirando la lista sin
    entender -- y sin un modal, que bloquea justo donde está decidiendo."""
    coord = _coordinador(tmp_path)
    qtbot.addWidget(coord.inicio)
    coord.mostrar_inicio()
    malo = tmp_path / "roto.cvproj"
    malo.write_text("no es json {")

    coord.inicio.abrir_pedido.emit(malo)

    assert coord.ventanas == []
    assert coord.inicio.isVisible()
    assert coord.inicio.aviso.isVisible()
    assert "roto.cvproj" in coord.inicio.aviso.text()


def test_el_aviso_no_sobrevive_al_siguiente_intento(qtbot, tmp_path):
    coord = _coordinador(tmp_path)
    qtbot.addWidget(coord.inicio)
    coord.mostrar_inicio()
    malo = tmp_path / "roto.cvproj"
    malo.write_text("no es json {")
    coord.inicio.abrir_pedido.emit(malo)

    coord.inicio.abrir_pedido.emit(_proyecto_en(tmp_path))

    assert coord.inicio.aviso.isHidden()
    coord.ventanas[0].close()


def test_proyecto_nuevo_pide_donde_guardarlo(qtbot, tmp_path, monkeypatch):
    destino = tmp_path / "Casa Nueva.cvproj"
    monkeypatch.setattr(QFileDialog, "getSaveFileName",
                        lambda *a, **k: (str(destino), ""))
    coord = _coordinador(tmp_path)
    qtbot.addWidget(coord.inicio)
    coord.mostrar_inicio()

    coord.inicio.nuevo_pedido.emit()

    assert destino.exists()
    assert coord.ventanas[0].project_name == "Casa Nueva"
    coord.ventanas[0].close()


def test_cancelar_el_selector_no_crea_nada(qtbot, tmp_path, monkeypatch):
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: ("", ""))
    coord = _coordinador(tmp_path)
    qtbot.addWidget(coord.inicio)
    coord.mostrar_inicio()

    coord.inicio.nuevo_pedido.emit()

    assert coord.ventanas == []
    assert coord.inicio.isVisible()


def test_al_proyecto_nuevo_se_le_pone_la_extension_si_falta(qtbot, tmp_path, monkeypatch):
    """El selector de macOS deja borrar la extension. Sin ella el archivo no
    se reconoce como proyecto la proxima vez."""
    monkeypatch.setattr(QFileDialog, "getSaveFileName",
                        lambda *a, **k: (str(tmp_path / "Sin extension"), ""))
    coord = _coordinador(tmp_path)
    qtbot.addWidget(coord.inicio)
    coord.mostrar_inicio()

    coord.inicio.nuevo_pedido.emit()

    assert (tmp_path / "Sin extension.cvproj").exists()
    coord.ventanas[0].close()


def test_abrir_otro_usa_el_selector_de_archivos(qtbot, tmp_path, monkeypatch):
    ruta = _proyecto_en(tmp_path)
    monkeypatch.setattr(QFileDialog, "getOpenFileName",
                        lambda *a, **k: (str(ruta), ""))
    coord = _coordinador(tmp_path)
    qtbot.addWidget(coord.inicio)
    coord.mostrar_inicio()

    coord.inicio.abrir_otro_pedido.emit()

    assert coord.ventanas[0].project_name == "P"
    coord.ventanas[0].close()


def test_quitar_un_reciente_lo_saca_de_la_lista(qtbot, tmp_path):
    coord = _coordinador(tmp_path)
    qtbot.addWidget(coord.inicio)
    ruta = _proyecto_en(tmp_path)
    coord.inicio.abrir_pedido.emit(ruta)
    coord.ventanas[0].close()
    assert coord.inicio.nombres_visibles() == ["P"]

    coord.inicio.quitar_pedido.emit(ruta)

    assert coord.inicio.nombres_visibles() == []


# --- main() ----------------------------------------------------------------


def test_main_aplica_el_stylesheet_global(qtbot, monkeypatch):
    from PySide6.QtWidgets import QApplication

    QApplication.instance().setStyleSheet("")

    class _CoordinadorFalso:
        def __init__(self, **kwargs):
            pass

        def migrar_lo_viejo(self):
            pass

        def mostrar_inicio(self):
            pass

    monkeypatch.setattr(app_module, "Coordinador", _CoordinadorFalso)
    monkeypatch.setattr(app_module.QApplication, "exec", lambda self: 0)
    monkeypatch.setattr(app_module.sys, "exit", lambda code=0: None)

    app_module.main()

    app = QApplication.instance()
    # el color exacto sale del tema, no se escribe a mano: si se fija un
    # hexadecimal aqui, la asercion queda obsoleta en silencio (paso: este
    # test afirmaba #08080a, un color que ya no existia en theme.py).
    assert f"background-color: {theme.BG_APP}" in app.styleSheet()


def test_un_tamano_ilegible_no_impide_abrir_el_proyecto(qtbot, tmp_path):
    """Al revés que con los clips: sin el tamaño la tarjeta cae en 16:9 y se
    ve raro —recuperable, y a la vista—, mientras que un clip perdido se
    lleva su clasificación sin dejar rastro."""
    ruta = _proyecto_en(tmp_path, {
        "tamanos": {"0": "no son dos numeros", "no-es-indice": [10, 20]},
        "duraciones": {"0": "larga"},
        "rotaciones": {"0": None},
        "bytes": {"0": "setecientos"},
        "rooms": "Sala",                 # ni siquiera es una lista
    })

    window = abrir_proyecto(ruta, video_factory=_FakeMpv,
                            recientes_path=tmp_path / "r.json")
    qtbot.addWidget(window)

    assert window is not None
    assert window._clip_sizes == {}
    assert window._clip_durations == {}
    assert window._bytes_guardados == {}
    assert window.room_selection.active_rooms() == []


def test_la_migracion_le_calcula_las_relativas_a_la_sesion_vieja(tmp_path):
    """`rutas_relativas` es léxica: no toca disco. La sesión vieja trae las
    rutas y los orígenes de sus bins, así que la relativa —lo único que
    permite reencontrar el material en otra computadora— se puede calcular
    ahí mismo, sin esperar a que la media esté conectada."""
    sesion = _sesion_vieja(tmp_path, {
        "bins": [{"nombre": "Sony", "origen": "/cam", "clips": [0]}],
    })
    destino = tmp_path / "convertido.cvproj"

    migrar_sesion(sesion, destino)

    assert abrir(destino)["relativas"] == {"0": "C0001.MP4"}


def test_una_sesion_con_clips_rotos_no_se_migra_a_medias(tmp_path):
    """Si no se pueden leer sus clips, el .cvproj que saliera de ahí tampoco
    se podría abrir. Mejor no crearlo y dejar la sesión donde está."""
    sesion = _sesion_vieja(tmp_path, {"clips": [{"orden": 1}]})

    assert migrar_sesion(sesion, tmp_path / "x.cvproj") is False
    assert not (tmp_path / "x.cvproj").exists()


def test_si_no_se_puede_escribir_el_proyecto_la_app_abre_igual(tmp_path, monkeypatch):
    """Migrar corre ANTES de que exista una ventana. Un traceback aquí deja a
    Bruno sin poder entrar a la app —por una carpeta que no era escribible,
    iCloud, TCC o el disco lleno—."""
    def no_se_puede(*a, **k):
        raise OSError("read-only file system")

    monkeypatch.setattr(app_module.proyecto, "guardar", no_se_puede)
    sesion = _sesion_vieja(tmp_path)

    resultado = migrar_sesion_vieja(sesion=sesion, carpeta=tmp_path / "docs",
                                    recientes_path=tmp_path / "r.json")

    assert resultado is None
    assert sesion.exists()          # y no se apartó: no hay nada a salvo


def test_si_falla_apartar_la_vieja_no_se_acumulan_copias(tmp_path, monkeypatch):
    """Si el `replace` falla después de escribir, no queda marca —y sin marca
    cada arranque volvería a convertirla: «(2)», «(3)», «(4)»…—. Así que lo
    recién escrito se deshace: la sesión sigue intacta, no se pierde nada y
    el siguiente arranque lo vuelve a intentar limpio."""
    real = app_module.os.replace
    monkeypatch.setattr(app_module.os, "replace",
                        _que_falla_al_apartar(real, tmp_path))
    sesion = _sesion_vieja(tmp_path)
    docs = tmp_path / "docs"

    primero = migrar_sesion_vieja(sesion=sesion, carpeta=docs,
                                  recientes_path=tmp_path / "r.json")
    monkeypatch.setattr(app_module.os, "replace", real)
    segundo = migrar_sesion_vieja(sesion=sesion, carpeta=docs,
                                  recientes_path=tmp_path / "r.json")

    assert primero is None
    assert segundo is not None
    assert sesion.exists() is False          # ya se apartó en el segundo
    assert len(list(docs.glob("*.cvproj"))) == 1


def _que_falla_al_apartar(real, tmp_path):
    """`os.replace` que solo revienta al apartar la sesión.

    No puede fallar siempre: `proyecto.guardar` también usa `os.replace` para
    su escritura atómica, y romper esa haría fallar el paso anterior en vez
    del que se quiere probar.
    """
    def falso(origen, destino):
        if str(origen).endswith("sesion.json"):
            raise OSError("no se pudo renombrar")
        return real(origen, destino)

    return falso


def test_apartar_la_vieja_no_pisa_una_anterior(tmp_path):
    """Hoy es inalcanzable, pero por una invariante que no está escrita: la
    sesión apartada es la copia de respaldo, y pisarla la borraría."""
    ya_estaba = tmp_path / "sesion.migrada.json"
    ya_estaba.write_text('{"lo": "de mucho antes"}')
    sesion = _sesion_vieja(tmp_path)

    migrar_sesion_vieja(sesion=sesion, carpeta=tmp_path / "docs",
                        recientes_path=tmp_path / "r.json")

    assert ya_estaba.read_text() == '{"lo": "de mucho antes"}'
    assert (tmp_path / "sesion.migrada.2.json").exists()


def test_la_migracion_lee_la_sesion_una_sola_vez(tmp_path, monkeypatch):
    lecturas = []
    real = app_module.load_session

    def contando(ruta):
        lecturas.append(ruta)
        return real(ruta)

    monkeypatch.setattr(app_module, "load_session", contando)
    sesion = _sesion_vieja(tmp_path)

    migrar_sesion_vieja(sesion=sesion, carpeta=tmp_path / "docs",
                        recientes_path=tmp_path / "r.json")

    assert len(lecturas) == 1


def test_migrar_al_arrancar_lo_deja_en_la_lista(qtbot, tmp_path):
    coord = _coordinador(tmp_path)
    qtbot.addWidget(coord.inicio)
    sesion = _sesion_vieja(tmp_path)

    coord.migrar_lo_viejo(sesion=sesion, carpeta=tmp_path / "docs")
    coord.mostrar_inicio()

    assert coord.inicio.nombres_visibles() == ["Lo de antes"]
    assert coord.inicio.aviso.isHidden()


def test_si_la_migracion_falla_la_app_abre_y_lo_dice(qtbot, tmp_path, monkeypatch):
    def no_se_puede(*a, **k):
        raise OSError("read-only file system")

    monkeypatch.setattr(app_module.proyecto, "guardar", no_se_puede)
    coord = _coordinador(tmp_path)
    qtbot.addWidget(coord.inicio)
    sesion = _sesion_vieja(tmp_path)

    coord.migrar_lo_viejo(sesion=sesion, carpeta=tmp_path / "docs")
    coord.mostrar_inicio()

    assert coord.inicio.isVisible()          # abrió igual, que es lo que importa
    assert coord.inicio.aviso.isVisible()
    assert sesion.exists()


def test_sin_sesion_vieja_el_arranque_no_dice_nada(qtbot, tmp_path):
    coord = _coordinador(tmp_path)
    qtbot.addWidget(coord.inicio)

    coord.migrar_lo_viejo(sesion=tmp_path / "no-esta.json",
                          carpeta=tmp_path / "docs")
    coord.mostrar_inicio()

    assert coord.inicio.aviso.isHidden()


def test_un_proyecto_nuevo_que_no_se_pudo_escribir_no_se_devuelve(qtbot, tmp_path):
    """`crear_proyecto` promete «vacío y YA guardado». Si la carpeta no era
    escribible devolvía la ventana igual y registraba un reciente que iba a
    salir apagado desde el primer día."""
    estorbo = tmp_path / "estorbo"
    estorbo.write_text("no soy una carpeta")
    recientes = tmp_path / "r.json"

    ventana = crear_proyecto(estorbo / "P.cvproj", "P", video_factory=_FakeMpv,
                             recientes_path=recientes)

    assert ventana is None
    from clasificador_video.recientes import Recientes
    assert Recientes(recientes).lista() == []


def test_si_el_proyecto_nuevo_no_se_puede_crear_se_dice(qtbot, tmp_path, monkeypatch):
    estorbo = tmp_path / "estorbo"
    estorbo.write_text("no soy una carpeta")
    monkeypatch.setattr(QFileDialog, "getSaveFileName",
                        lambda *a, **k: (str(estorbo / "P.cvproj"), ""))
    coord = _coordinador(tmp_path)
    qtbot.addWidget(coord.inicio)
    coord.mostrar_inicio()

    coord.inicio.nuevo_pedido.emit()

    assert coord.ventanas == []
    assert coord.inicio.isVisible()
    assert coord.inicio.aviso.isVisible()


class _RelojFalso:
    """Un reloj que avanza cuando se le dice. La fecha de un reciente se
    escribe con `datetime.now()`, y sin fijarla no se puede distinguir la
    hora de abrir de la de cerrar."""

    def __init__(self, momentos):
        self._momentos = list(momentos)

    def now(self):
        return self._momentos.pop(0) if self._momentos else self._ultimo


def test_la_fecha_del_reciente_es_la_de_la_ultima_vez_que_trabajaste(qtbot, tmp_path, monkeypatch):
    """Guardaba cuándo lo ABRISTE, y la lista se ordena por ese dato.

    Abres un proyecto a las 9 y trabajas en él toda la tarde: la lista sigue
    diciendo 9:00, y basta con que a mediodía hayas abierto otro un minuto
    para que ese otro te quede arriba. Se ordena por lo que menos importa.
    """
    import datetime as _datetime

    from clasificador_video.recientes import Recientes

    reloj = _RelojFalso([
        _datetime.datetime(2026, 8, 9, 9, 0),      # al abrirlo
        _datetime.datetime(2026, 8, 9, 18, 30),    # al cerrarlo
    ])
    reloj._ultimo = _datetime.datetime(2026, 8, 9, 18, 30)
    monkeypatch.setattr("clasificador_video.recientes.datetime", reloj)
    recientes = tmp_path / "r.json"
    coord = Coordinador(recientes_path=recientes, video_factory=_FakeMpv)
    qtbot.addWidget(coord.inicio)
    coord.inicio.abrir_pedido.emit(_proyecto_en(tmp_path))

    coord.ventanas[0].close()

    assert Recientes(recientes).lista()[0].cuando == "2026-08-09 18:30"


def test_la_version_vive_en_un_solo_lugar():
    """El instalable y la app tienen que decir lo MISMO.

    Hasta la 1.2 la version solo existia en la receta de empaquetado, o sea
    que la app no la sabia y no habia forma de preguntarsela: para averiguar
    que version tenias habia que salirte al Finder. Y escrita en dos lados,
    tarde o temprano dirian cosas distintas y nadie sabria cual es la buena.
    """
    import clasificador_video

    assert clasificador_video.__version__


def test_la_receta_del_instalable_lee_esa_misma_version():
    """La receta NO puede tener su propio numero: es el que macOS pone en
    «Obtener informacion», y si se separa del de la app, la que dice el
    Finder y la que dice la pantalla de inicio se contradicen."""
    from pathlib import Path

    receta = (Path(__file__).resolve().parents[1]
              / "empaque" / "clasificador.spec").read_text()

    assert "__version__" in receta
