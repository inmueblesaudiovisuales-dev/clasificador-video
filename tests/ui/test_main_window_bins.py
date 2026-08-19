# tests/ui/test_main_window_bins.py
import json
from pathlib import Path

import pytest

from clasificador_video.manifest import Clip
from clasificador_video.proyecto import rutas_relativas
from clasificador_video.rooms import RoomSelection
from clasificador_video.ui.clip_sheet import SIN_BIN
from clasificador_video.ui.main_window import MainWindow


class FakeMpv:
    """Sustituto de `mpv.MPV`. Mismo doble que usa `test_main_window.py`.

    Sin el, cada ventana de este archivo abre un mpv de verdad --con sus
    hilos-- solo para que `_abrir_clip_actual` tenga a quien hablarle.
    """

    def __init__(self, **kwargs):
        self.init_kwargs = kwargs
        self.loaded_path = None
        self.pause = True
        self.time_pos = 0.0
        self.commands = []

    def play(self, path):
        self.loaded_path = path

    def command(self, *args):
        self.commands.append(args)


def _clip(i, ruta):
    return Clip(orden=i + 1, ruta=Path(ruta), categoria_path=[], fps=30.0)


def _probe_falso(path):
    """Sondeo que no toca disco ni lanza ffprobe de verdad.

    Las tareas 5, 6 y 7 del plan escriben tests con rutas inventadas
    (`/cam/A.MP4`) que llaman a medir y sondear proxies. Sin este doble,
    esos tests lanzarian ffprobe de verdad contra archivos que no existen.
    """
    return {
        "fps": 30.0,
        "duration_frames": 300,
        "width": 1080,
        "height": 1920,
        "rotation": 0,
    }


@pytest.fixture(autouse=True)
def confirmar_por_defecto(monkeypatch):
    """«Quitar del proyecto» pregunta antes, y un cartel modal cuelga la
    suite bajo `offscreen`. Por defecto se contesta que si, para que cada
    test hable de lo suyo; los dos que prueban el cartel vuelven a
    parchearlo con lo que necesitan y ganan, porque se aplica despues.
    """
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "question",
                        lambda *a, **k: QMessageBox.StandardButton.Yes)


@pytest.fixture
def ventana(qtbot):
    """Misma forma que `_window` en test_main_window.py -- no hay una
    fixture equivalente ya declarada en tests/ui/, asi que se copia el
    patron en vez de duplicar la logica en cada archivo nuevo."""
    window = MainWindow(project_name="Casa Jardin", room_selection=RoomSelection(),
                        video_factory=FakeMpv)
    window._probe_clip = _probe_falso
    qtbot.addWidget(window)
    return window


def test_el_autosave_escribe_los_bins(qtbot, tmp_path, ventana):
    ventana.session_path = tmp_path / "sesion.json"
    ventana.load_clips([_clip(0, "/dron/A.MP4"), _clip(1, "/dron/B.MP4")])
    ventana.bins.agregar("Dron", Path("/dron"), [0, 1])

    ventana._write_autosave_now()
    # si el trabajo de escritura no termino en el plazo, la aserción de
    # abajo fallaria con FileNotFoundError -- que no dice nada del timeout
    # real. Afirmar esto primero deja el error correcto si algun dia pasa.
    assert ventana._autosave_pool.waitForDone(2000)

    data = json.loads((tmp_path / "sesion.json").read_text())
    assert data["bins"] == [
        {"nombre": "Dron", "origen": "/dron", "clips": [0, 1]}
    ]


def test_cargar_clips_de_nuevo_reinicia_los_bins(qtbot, ventana):
    """`load_clips` ya limpia el historial y los proxies porque van por
    INDICE de clip y una lista nueva vuelve invalidos esos indices. Los
    bins son exactamente el mismo caso y se habian quedado afuera: sin
    esto, restaurar una sesion de 109 clips e importar otra carpeta deja
    bins apuntando a clips que ya no son esos.
    """
    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/cam/B.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0, 1])

    ventana.load_clips([_clip(0, "/dron/D.MP4")])

    assert ventana.bins.nombres() == []


def test_agregar_clips_conserva_los_proxies_ya_enganchados(qtbot, ventana):
    ventana.load_clips([_clip(0, "/cam/A.MP4")])
    ventana.clips[0].ruta_proxy = Path("/cam/AS03.MP4")
    ventana._proxy_sizes[0] = (1080, 1920)

    ventana.agregar_clips([_clip(1, "/dron/D.MP4")], nombre_de_bin="Dron",
                          origen=Path("/dron"))

    assert ventana.clips[0].ruta_proxy == Path("/cam/AS03.MP4")
    assert ventana._proxy_sizes[0] == (1080, 1920)
    assert len(ventana.clips) == 2


def test_agregar_clips_conserva_el_historial(qtbot, ventana):
    ventana.load_clips([_clip(0, "/cam/A.MP4")])
    # el metodo real de clasificar: el plan lo llamaba `clasificar`, que no
    # existe en el codigo.
    ventana._apply_categoria_to_targets(["Cocina"])
    cuantas = len(ventana.history.entries())

    ventana.agregar_clips([_clip(1, "/dron/D.MP4")], nombre_de_bin="Dron",
                          origen=Path("/dron"))

    assert cuantas == 1
    assert len(ventana.history.entries()) == cuantas


def test_agregar_clips_crea_el_bin_con_los_indices_nuevos(qtbot, ventana):
    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/cam/B.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0, 1])

    ventana.agregar_clips([_clip(2, "/dron/D.MP4")], nombre_de_bin="Dron",
                          origen=Path("/dron"))

    assert ventana.bins.nombres() == ["Sony", "Dron"]
    assert ventana.bins.clips_de("Dron") == [2]


def test_agregar_al_mismo_bin_le_suma_los_indices(qtbot, ventana):
    """Importar dos veces la misma tarjeta no crea «Sony» y «Sony 2»."""
    ventana.load_clips([_clip(0, "/cam/A.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0])

    ventana.agregar_clips([_clip(1, "/cam/B.MP4")], nombre_de_bin="Sony",
                          origen=Path("/cam"))

    assert ventana.bins.nombres() == ["Sony"]
    assert ventana.bins.clips_de("Sony") == [0, 1]


def test_soltar_otra_tarjeta_sobre_el_mismo_bin_amplia_su_origen(qtbot, ventana):
    """La segunda tarjeta de la Sony viene de otra carpeta. Si el origen del
    bin se quedara en el de la primera, esos clips no tendrian ruta relativa
    y al abrir el proyecto en otra computadora saldrian como «no
    encontrados» aunque el archivo este ahi."""
    ventana.load_clips([_clip(0, "/Volumes/DISCO/tarjeta1/A.MP4")])
    ventana.bins.agregar("Sony", Path("/Volumes/DISCO/tarjeta1"), [0])

    ventana.agregar_clips([_clip(1, "/Volumes/DISCO/tarjeta2/B.MP4")],
                          nombre_de_bin="Sony",
                          origen=Path("/Volumes/DISCO/tarjeta2"))

    assert ventana.bins.origen_de("Sony") == Path("/Volumes/DISCO")


def test_agregar_clips_renumera_el_orden_de_los_nuevos(qtbot, ventana):
    """`orden` es el numero que se ve en la tarjeta y el que viaja al
    manifest: dos clips con el mismo numero serian dos «clip 001»."""
    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/cam/B.MP4")])

    ventana.agregar_clips([_clip(0, "/dron/D.MP4")], nombre_de_bin="Dron",
                          origen=Path("/dron"))

    assert [c.orden for c in ventana.clips] == [1, 2, 3]


def test_agregar_clips_no_recrea_las_tarjetas_que_ya_estaban(qtbot, ventana):
    """El bug de Bruno visto desde la ventana: la portada vive en la
    tarjeta, y reconstruir la hoja se la lleva."""
    ventana.load_clips([_clip(0, "/cam/A.MP4")])
    antes = ventana.clip_sheet.item_widgets[0]

    ventana.agregar_clips([_clip(1, "/dron/D.MP4")], nombre_de_bin="Dron",
                          origen=Path("/dron"))

    assert ventana.clip_sheet.item_widgets[0] is antes
    assert ventana.clip_sheet.count() == 2


def _carpeta_con(tmp_path, nombre, *archivos):
    carpeta = tmp_path / nombre
    carpeta.mkdir()
    for a in archivos:
        (carpeta / a).touch()
    return carpeta


def test_importar_una_segunda_carpeta_no_recrea_las_tarjetas(qtbot, tmp_path,
                                                             monkeypatch, ventana):
    """EL bug que Bruno reporto, de punta a punta: la portada vive en la
    tarjeta y la importacion la destruia."""
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.extract_thumbnail_strip", lambda *a, **k: []
    )
    sony = _carpeta_con(tmp_path, "FX30", "C0001.MP4", "C0002.MP4")
    dron = _carpeta_con(tmp_path, "DRON", "DJI_0001.MP4")

    ventana.importar_rutas([sony])
    antes = list(ventana.clip_sheet.item_widgets)
    ventana.importar_rutas([dron])

    assert ventana.clip_sheet.item_widgets[:2] == antes
    assert ventana.bins.nombres() == ["FX30", "DRON"]
    assert ventana.bins.clips_de("DRON") == [2]
    assert [c.orden for c in ventana.clips] == [1, 2, 3]


def test_importar_la_misma_carpeta_dos_veces_no_duplica(qtbot, tmp_path,
                                                        monkeypatch, ventana,
                                                        avisos):
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.extract_thumbnail_strip", lambda *a, **k: []
    )
    sony = _carpeta_con(tmp_path, "FX30", "C0001.MP4")

    ventana.importar_rutas([sony])
    ventana.importar_rutas([sony])

    assert len(ventana.clips) == 1
    assert ventana.bins.nombres() == ["FX30"]


def test_importar_con_la_app_vacia_abre_el_primer_clip(qtbot, tmp_path,
                                                       monkeypatch, ventana):
    """`load_clips` terminaba abriendo el clip; al pasar la importacion por
    `agregar_clips` eso se perdio y la app quedaba con la hoja llena y el
    visor en negro hasta que hicieras clic."""
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.extract_thumbnail_strip", lambda *a, **k: []
    )
    sony = _carpeta_con(tmp_path, "FX30", "C0001.MP4", "C0002.MP4")
    abiertos = []
    monkeypatch.setattr(ventana, "_abrir_clip_actual",
                        lambda: abiertos.append(ventana.current_index))

    ventana.importar_rutas([sony])

    assert abiertos == [0]


def test_agregar_material_no_saca_a_bruno_del_clip_donde_estaba(qtbot, monkeypatch,
                                                                ventana):
    """Solo se abre cuando NO habia nada abierto. Saltar al primero de la
    carpeta nueva seria perder el lugar de trabajo a media clasificacion."""
    ventana.load_clips([_clip(i, f"/cam/C{i:04d}.MP4") for i in range(41)])
    ventana.current_index = 40
    abiertos = []
    monkeypatch.setattr(ventana, "_abrir_clip_actual",
                        lambda: abiertos.append(ventana.current_index))

    ventana.agregar_clips([_clip(41, "/dron/D.MP4")], nombre_de_bin="Dron",
                          origen=Path("/dron"))

    assert abiertos == []
    assert ventana.current_index == 40


class _PoolEspia:
    """Cola falsa: registra los trabajos en vez de correrlos."""

    def __init__(self):
        self.jobs = []

    def start(self, job, *a, **k):
        self.jobs.append(job)

    def waitForDone(self, *a, **k):
        # la ventana lo llama al cerrarse
        return True


def test_agregar_material_solo_pide_las_portadas_de_los_clips_nuevos(
        qtbot, tmp_path, monkeypatch, ventana):
    """Spec §6. Antes se re-encolaban los 109 clips viejos ademas de los
    nuevos, se invalidaban los trabajos del primer lote que seguian en
    vuelo y quedaban DOS trabajos para el mismo clip compartiendo carpeta
    y socket IPC, con uno borrandole el socket al otro. Ese es el «se me
    prendieron los abanicos sin hacer nada» que reporto Bruno.
    """
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.extract_thumbnail_strip", lambda *a, **k: []
    )
    sony = _carpeta_con(tmp_path, "FX30", "C0001.MP4", "C0002.MP4")
    dron = _carpeta_con(tmp_path, "DRON", "DJI_0001.MP4")
    ventana.importar_rutas([sony])
    generacion = ventana._thumb_generation
    espia = _PoolEspia()
    monkeypatch.setattr(ventana, "_thread_pool", espia)

    ventana.importar_rutas([dron])

    assert [j.index for j in espia.jobs] == [2]
    # y la generacion NO sube: subirla tira las señales de los trabajos del
    # primer lote que todavia no llegaron.
    assert ventana._thumb_generation == generacion


def _con_medidas(ventana, *indices):
    """Un original medido para cada indice.

    `_el_proxy_calza` compara contra `_clip_durations` y `_clip_sizes`: sin
    ellos descarta todo y los tests de abajo pasarian por la razon
    equivocada.
    """
    for i in indices:
        ventana._clip_durations[i] = 10.0   # 300 cuadros a 30 fps
        ventana._clip_sizes[i] = (1080, 1920)


_INFO_QUE_CALZA = {"fps": 30.0, "duration_frames": 300,
                   "width": 540, "height": 960, "rotation": 0}


def test_enganchar_los_proxies_de_un_bin_no_borra_los_del_otro(qtbot, ventana):
    """El bug que este plan existe para no cometer.

    `_sondear_proxies` arrancaba con `_proxy_sizes = {}`. Al volverse por
    bin, eso borraria los proxies de la camara que no estas tocando.
    """
    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/dron/D.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0])
    ventana.bins.agregar("Dron", Path("/dron"), [1])
    ventana.clips[0].ruta_proxy = Path("/cam/AS03.MP4")
    ventana._proxy_sizes[0] = (1080, 1920)
    ventana._proxy_candidatos[0] = Path("/cam/AS03.MP4")

    ventana._sondear_proxies({Path("/dron/D.MP4"): Path("/dron/DPROXY.MP4")},
                             indices=[1])

    assert ventana.clips[0].ruta_proxy == Path("/cam/AS03.MP4")
    assert ventana._proxy_sizes[0] == (1080, 1920)
    assert ventana._proxy_candidatos[0] == Path("/cam/AS03.MP4")


def test_volver_a_enganchar_el_mismo_bin_si_limpia_lo_suyo(qtbot, ventana):
    ventana.load_clips([_clip(0, "/dron/D.MP4")])
    ventana.bins.agregar("Dron", Path("/dron"), [0])
    ventana.clips[0].ruta_proxy = Path("/dron/VIEJO.MP4")
    ventana._proxy_sizes[0] = (1080, 1920)

    ventana._sondear_proxies({Path("/dron/D.MP4"): None}, indices=[0])

    assert ventana.clips[0].ruta_proxy is None
    assert 0 not in ventana._proxy_sizes


def test_sin_indices_el_sondeo_sigue_alcanzando_a_todos(qtbot, ventana):
    """`indices=None` es el alcance de siempre: todo el proyecto. Lo usa
    `load_clips` y lo usaria cualquier llamada vieja."""
    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/cam/B.MP4")])
    ventana.clips[0].ruta_proxy = Path("/cam/AS03.MP4")
    ventana.clips[1].ruta_proxy = Path("/cam/BS03.MP4")

    ventana._sondear_proxies({})

    assert [c.ruta_proxy for c in ventana.clips] == [None, None]


def test_un_sondeo_del_otro_bin_que_llega_tarde_sigue_contando(qtbot, monkeypatch,
                                                               ventana):
    """`_proxy_generation` es global: subirla al enganchar el dron
    descartaba los trabajos de la Sony que seguian en vuelo, y esos
    resultados se perdian sin que nada lo dijera. La generacion se compara
    ahora por clip, no contra el contador global."""
    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/dron/D.MP4")])
    _con_medidas(ventana, 0, 1)
    espia = _PoolEspia()
    monkeypatch.setattr(ventana, "_thread_pool", espia)

    ventana._sondear_proxies({Path("/cam/A.MP4"): Path("/cam/AS03.MP4")},
                             indices=[0])
    sondeos = [j for j in espia.jobs if hasattr(j, "proxy")]
    ventana._sondear_proxies({Path("/dron/D.MP4"): Path("/dron/DP.MP4")},
                             indices=[1])

    ventana._on_proxy_sondeado(sondeos[0]._generation, 0, dict(_INFO_QUE_CALZA))

    assert ventana.clips[0].ruta_proxy == Path("/cam/AS03.MP4")


def test_un_sondeo_viejo_del_MISMO_bin_se_sigue_descartando(qtbot, monkeypatch,
                                                            ventana):
    """La otra mitad: volver a enganchar el mismo bin si invalida lo que
    quedo corriendo, o el resultado viejo pisaria al nuevo."""
    ventana.load_clips([_clip(0, "/cam/A.MP4")])
    _con_medidas(ventana, 0)
    espia = _PoolEspia()
    monkeypatch.setattr(ventana, "_thread_pool", espia)

    ventana._sondear_proxies({Path("/cam/A.MP4"): Path("/cam/VIEJO.MP4")},
                             indices=[0])
    viejo = [j for j in espia.jobs if hasattr(j, "proxy")][0]
    ventana._sondear_proxies({Path("/cam/A.MP4"): Path("/cam/NUEVO.MP4")},
                             indices=[0])

    ventana._on_proxy_sondeado(viejo._generation, 0, dict(_INFO_QUE_CALZA))

    assert ventana.clips[0].ruta_proxy is None


def _sondeos(espia):
    """Solo `_ProxyProbeJob` es el que trae `proxy`; el otro es de portadas."""
    return [j for j in espia.jobs if hasattr(j, "proxy")]


def _portadas(espia):
    return [j for j in espia.jobs if not hasattr(j, "proxy")]


def test_sondear_un_bin_no_vuelve_a_pedir_las_portadas_del_otro(qtbot, monkeypatch,
                                                                 ventana):
    """`_sondear_proxies` acotaba todo lo suyo al bin y despues llamaba a
    `_schedule_thumbnails()` SIN indices, que sube la generacion y recorre
    todos los clips. Con la Sony todavia sacando portadas, enganchar los
    proxies del dron le tiraba las señales en vuelo y le encolaba un segundo
    trabajo por clip, sobre la misma carpeta y el mismo socket: los
    abanicos girando sin haber hecho nada.
    """
    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/dron/D.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0])
    ventana.bins.agregar("Dron", Path("/dron"), [1])
    generacion = ventana._thumb_generation
    espia = _PoolEspia()
    monkeypatch.setattr(ventana, "_thread_pool", espia)

    ventana._sondear_proxies({Path("/dron/D.MP4"): Path("/dron/DP.MP4")},
                             indices=[1])

    assert [j.index for j in _portadas(espia)] == [1]
    assert ventana._thumb_generation == generacion


def test_re_enlazar_un_bin_no_infla_el_total_de_portadas(qtbot, monkeypatch,
                                                          ventana):
    """El total es cuantas portadas tiene el proyecto. Sumarle el bin cada
    vez que re-enlazas daria «113 de 115» con 109 clips."""
    ventana.load_clips([_clip(i, f"/cam/C{i:04d}.MP4") for i in range(3)])
    ventana.bins.agregar("Sony", Path("/cam"), [0, 1, 2])
    monkeypatch.setattr(ventana, "_thread_pool", _PoolEspia())

    ventana._sondear_proxies({}, indices=[0, 1, 2])
    ventana._sondear_proxies({}, indices=[0, 1, 2])

    assert ventana._miniaturas_totales == 3


def test_quitar_los_proxies_de_un_bin_se_guarda(qtbot, tmp_path, ventana):
    """`ruta_proxy` viaja en `Clip.to_dict()`, o sea que se persiste. Sin
    guardar, los proxies que quitaste estan de vuelta al reabrir la app."""
    ventana.session_path = tmp_path / "sesion.json"
    _dos_bins(ventana)
    ventana.clips[0].ruta_proxy = Path("/cam/C0001S03.MP4")
    ventana.clips[1].ruta_proxy = Path("/dron/DJI_0001_proxy.MP4")
    # `load_clips` ya dejo el debounce corriendo: sin apagarlo, la asercion
    # de abajo pasaria sola aunque quitar no guardara nada.
    ventana._autosave_timer.stop()

    ventana.quitar_proxies_de_bin("Dron")

    # el autosave con debounce quedo agendado, no se perdio
    assert ventana._autosave_timer.isActive()
    ventana._write_autosave_now()
    assert ventana._autosave_pool.waitForDone(2000)
    data = json.loads((tmp_path / "sesion.json").read_text())
    assert [c["ruta_proxy"] for c in data["clips"]] == ["/cam/C0001S03.MP4", None]


def test_quitar_los_proxies_de_un_bin_actualiza_la_barra(qtbot, monkeypatch,
                                                          ventana):
    """Si no se refresca, la barra sigue diciendo «2 proxies» de unos que
    ya no estan enganchados."""
    _dos_bins(ventana)
    ventana.clips[0].ruta_proxy = Path("/cam/C0001S03.MP4")
    ventana.clips[1].ruta_proxy = Path("/dron/DJI_0001_proxy.MP4")
    dichos = []
    monkeypatch.setattr(ventana.status_bar, "set_proxies",
                        lambda *a, **k: dichos.append(a))

    ventana.quitar_proxies_de_bin("Dron")

    assert dichos and dichos[-1][0] == 1


def test_un_bin_con_indices_de_mas_no_revienta(qtbot, ventana):
    """`app.py` toma los bins del JSON sin recortarlos contra los clips que
    de verdad se cargaron: una sesion desincronizada daba IndexError en el
    clic, en vez de simplemente no encontrar esos clips."""
    ventana.load_clips([_clip(0, "/cam/A.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0, 1, 7])

    ventana.quitar_proxies_de_bin("Sony")

    assert ventana.clips[0].ruta_proxy is None


def _dos_bins(ventana):
    ventana.load_clips([_clip(0, "/cam/C0001.MP4"), _clip(1, "/dron/DJI_0001.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0])
    ventana.bins.agregar("Dron", Path("/dron"), [1])


def test_el_patron_se_busca_solo_entre_los_clips_del_bin(qtbot, ventana, monkeypatch,
                                                         avisos):
    """La Sony nombra sus proxies con S03 y el dron con otra cosa. Con un
    solo patron para todo el proyecto, una de las dos se queda sin proxy.
    """
    _dos_bins(ventana)
    vistos = {}
    monkeypatch.setattr(ventana, "_sondear_proxies",
                        lambda emp, indices=None: vistos.update(emp=emp, idx=indices))

    ventana.adjuntar_proxies_de_bin(
        "Dron", elegido=Path("/dron/proxies/DJI_0001_proxy.MP4")
    )

    assert vistos["idx"] == [1]
    assert Path("/cam/C0001.MP4") not in vistos["emp"]


def test_el_contador_cuenta_contra_el_bin_y_no_contra_el_proyecto(
        qtbot, ventana, monkeypatch, avisos):
    """«Se encontraron 0 de 109» cuando el bin tiene 1 clip seria mentira."""
    _dos_bins(ventana)
    monkeypatch.setattr(ventana, "_sondear_proxies", lambda emp, indices=None: None)

    ventana.adjuntar_proxies_de_bin(
        "Dron", elegido=Path("/dron/proxies/DJI_0001_proxy.MP4")
    )

    assert "0 de 1" in avisos[0][1]


def test_la_referencia_es_el_clip_actual_si_es_de_ese_bin(qtbot, ventana,
                                                          monkeypatch, avisos):
    """Spec §5.1. Si eliges el proxy mirando el clip que tienes abierto, el
    patron tiene que salir de ESE par -- deducirlo contra el primero del bin
    daria un patron que no corresponde a nada."""
    ventana.load_clips([_clip(0, "/dron/DJI_0001.MP4"), _clip(1, "/dron/DJI_0002.MP4")])
    ventana.bins.agregar("Dron", Path("/dron"), [0, 1])
    ventana.current_index = 1
    vistos = {}
    monkeypatch.setattr(ventana, "_sondear_proxies",
                        lambda emp, indices=None: vistos.update(emp=emp))

    ventana.adjuntar_proxies_de_bin(
        "Dron", elegido=Path("/dron/proxies/DJI_0002_proxy.MP4")
    )

    # el patron salio de DJI_0002 (sufijo `_proxy`), asi que el otro clip se
    # busca como DJI_0001_proxy y no queda fuera del emparejado
    assert set(vistos["emp"]) == {Path("/dron/DJI_0001.MP4"),
                                  Path("/dron/DJI_0002.MP4")}


def test_un_archivo_que_no_corresponde_avisa_y_no_sondea(qtbot, ventana,
                                                          monkeypatch):
    _dos_bins(ventana)
    quejas = []
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.QMessageBox.warning",
        lambda parent, titulo, texto, *a, **k: quejas.append(titulo),
    )
    monkeypatch.setattr(ventana, "_sondear_proxies",
                        lambda *a, **k: pytest.fail("no debio sondear nada"))

    ventana.adjuntar_proxies_de_bin("Dron", elegido=Path("/dron/otra_cosa.MP4"))

    assert quejas == ["Ese archivo no corresponde"]


def test_quitar_los_proxies_de_un_bin_no_toca_al_otro(qtbot, ventana):
    _dos_bins(ventana)
    ventana.clips[0].ruta_proxy = Path("/cam/C0001S03.MP4")
    ventana.clips[1].ruta_proxy = Path("/dron/DJI_0001_proxy.MP4")

    ventana.quitar_proxies_de_bin("Dron")

    assert ventana.clips[0].ruta_proxy == Path("/cam/C0001S03.MP4")
    assert ventana.clips[1].ruta_proxy is None


def test_el_boton_de_la_barra_aplica_al_bin_del_clip_actual(qtbot, ventana,
                                                             monkeypatch):
    """Ya no tiene sentido como accion global: el patron es de una camara."""
    _dos_bins(ventana)
    ventana.current_index = 1
    pedidos = []
    monkeypatch.setattr(ventana, "adjuntar_proxies_de_bin",
                        lambda nombre, elegido=None: pedidos.append(nombre))

    ventana.adjuntar_proxies()

    assert pedidos == ["Dron"]


def test_el_boton_sin_bin_avisa_en_vez_de_no_hacer_nada(qtbot, ventana,
                                                         monkeypatch):
    quejas = []
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.QMessageBox.warning",
        lambda parent, titulo, texto, *a, **k: quejas.append(titulo),
    )

    ventana.adjuntar_proxies()

    assert quejas == ["Sin material"]


@pytest.fixture
def avisos(monkeypatch):
    """Cachar los QMessageBox: son modales y bajo offscreen cuelgan la suite."""
    vistos = []
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.QMessageBox.information",
        lambda parent, titulo, texto, *a, **k: vistos.append((titulo, texto)),
    )
    return vistos


def test_importar_algo_sin_videos_lo_dice(qtbot, tmp_path, ventana, avisos):
    """Spec §4.3: si nada de lo que soltaste es video, se dice por que en
    vez de no pasar nada."""
    carpeta = _carpeta_con(tmp_path, "DOCS", "notas.txt", "hoja.pdf")

    ventana.importar_rutas([carpeta])

    assert len(avisos) == 1
    assert avisos[0][0] == "Nada que importar"
    assert not ventana.clips


def test_importar_lo_que_ya_esta_lo_dice_con_otras_palabras(
        qtbot, tmp_path, monkeypatch, ventana, avisos):
    """Los dos casos se ven igual --no pasa nada-- y son distintos: en uno
    elegiste la carpeta equivocada y en el otro ya la habias importado."""
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.extract_thumbnail_strip", lambda *a, **k: []
    )
    sony = _carpeta_con(tmp_path, "FX30", "C0001.MP4")
    ventana.importar_rutas([sony])
    avisos.clear()

    ventana.importar_rutas([sony])

    assert len(avisos) == 1
    assert avisos[0][0] == "Ya están en el proyecto"
    assert len(ventana.clips) == 1


# --- F4 Task 10: el menu del bin conectado a la ventana ----------------------


def test_renombrar_un_bin_cambia_el_dato_y_la_hoja(qtbot, ventana):
    ventana.load_clips([_clip(0, "/dron/D.MP4")])
    ventana.bins.agregar("Dron", Path("/dron"), [0])

    ventana._on_bin_renombrado("Dron", "Dron DJI")

    assert ventana.bins.nombres() == ["Dron DJI"]
    assert ventana.clip_sheet.bin_headers() == ["Dron DJI"]


def test_la_hoja_dibuja_un_encabezado_por_bin_de_la_ventana(qtbot, ventana):
    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/dron/D.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0])
    ventana.bins.agregar("Dron", Path("/dron"), [1])

    ventana._refresh_sheet()

    assert ventana.clip_sheet.bin_headers() == ["Sony", "Dron"]
    assert ventana.clip_sheet.bin_header_widget("Sony").source_label.text() == "cam"


def test_el_encabezado_dice_cuantos_proxies_engancharon(qtbot, ventana):
    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/cam/B.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0, 1])
    ventana.clips[0].ruta_proxy = Path("/cam/A_S03.MP4")

    ventana._refresh_sheet()

    insignia = ventana.clip_sheet.bin_header_widget("Sony").proxy_badge
    assert insignia.text() == "proxy · 1/2"


def test_quitar_un_bin_corre_todo_lo_que_va_por_indice(qtbot, ventana):
    """El segundo lugar donde esto rompe en silencio.

    `_clip_durations`, `_clip_sizes`, `_clip_rotations`, `_proxy_sizes` y
    `_proxy_candidatos` van TODOS por indice de clip. Al quitar los clips 0
    y 1, el que era 2 pasa a ser 0 -- y cualquiera de esos diccionarios que
    no se corra queda describiendo a otro clip, sin dar ningun sintoma hasta
    que un video se dibuja acostado o un rango cae corrido.

    `_proxy_generacion_de` es el unico que NO se corre: se tira entero, por
    lo que explica `test_quitar_un_bin_invalida_los_sondeos_de_proxy_en_vuelo`.
    """
    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/cam/B.MP4"),
                        _clip(2, "/dron/D.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0, 1])
    ventana.bins.agregar("Dron", Path("/dron"), [2])
    ventana._clip_sizes = {0: (100, 200), 1: (100, 200), 2: (1920, 1080)}
    ventana._clip_durations = {0: 1.0, 1: 2.0, 2: 3.0}
    ventana._clip_rotations = {0: 0, 1: 0, 2: 90}
    ventana._proxy_sizes = {2: (640, 360)}
    ventana._proxy_candidatos = {2: Path("/dron/D_px.MP4")}
    ventana._proxy_generacion_de = {2: 7}

    ventana._on_bin_quitado("Sony")

    assert [c.ruta for c in ventana.clips] == [Path("/dron/D.MP4")]
    assert ventana.bins.clips_de("Dron") == [0]
    assert ventana._clip_sizes == {0: (1920, 1080)}
    assert ventana._clip_durations == {0: 3.0}
    assert ventana._clip_rotations == {0: 90}
    assert ventana._proxy_sizes == {0: (640, 360)}
    assert ventana._proxy_candidatos == {0: Path("/dron/D_px.MP4")}


def test_quitar_un_bin_corre_lo_que_dijo_la_ultima_revision(qtbot, ventana,
                                                            monkeypatch):
    """`_faltantes` va por indice igual que todo lo demas, y quien lo lee no
    puede esperar a la revision nueva.

    `_schedule_thumbnails` corre en el acto --dentro de `_on_bin_quitado`-- y
    se salta los clips cuyo archivo no esta. Con los indices sin correr, el
    clip que hereda un indice «faltante» se saltaba su extraccion, y la
    revision que se pide al final llega despues y no pide portadas: la
    tarjeta se quedaba gris hasta cerrar y reabrir el proyecto.
    """
    from clasificador_video.ui.main_window import _ThumbnailJob

    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/cam/B.MP4"),
                        _clip(2, "/dron/D.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0, 1])
    ventana.bins.agregar("Dron", Path("/dron"), [2])
    ventana._clip_durations = {0: 1.0, 1: 2.0, 2: 3.0}
    # la ultima revision dijo: los dos de la Sony no estan en disco
    ventana._faltantes = {0, 1}
    ventana._proxies_perdidos = {1: "BS03.MP4"}

    pedidas = []
    monkeypatch.setattr(
        ventana._thread_pool, "start",
        lambda job, *a, **k: pedidas.append(job.index)
        if isinstance(job, _ThumbnailJob) else None,
    )
    ventana._on_bin_quitado("Sony")

    assert ventana._faltantes == set()
    assert ventana._proxies_perdidos == {}
    # el del dron ahora es el 0, su archivo si estaba: se le pide su portada
    assert pedidas == [0]


def test_quitar_un_bin_renumera_los_clips_que_quedan(qtbot, ventana):
    """`orden` es el numero que se ve en la tarjeta y el que viaja al
    manifest: dejar un proyecto que empieza en el clip 3 seria mentira."""
    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/dron/D.MP4"),
                        _clip(2, "/dron/E.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0])
    ventana.bins.agregar("Dron", Path("/dron"), [1, 2])

    ventana._on_bin_quitado("Sony")

    assert [c.orden for c in ventana.clips] == [1, 2]


def test_quitar_un_bin_limpia_el_historial(qtbot, ventana):
    """El historial guarda INDICES de clip: despues de correrlos ya no
    apunta a lo mismo, y deshacer moveria el clip equivocado."""
    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/dron/D.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0])
    ventana.bins.agregar("Dron", Path("/dron"), [1])
    ventana.select_clip(1)
    ventana.handle_key_press("p")
    assert ventana.history.entries()

    ventana._on_bin_quitado("Sony")

    assert ventana.history.entries() == []


def test_quitar_el_ultimo_bin_deja_el_proyecto_vacio_sin_reventar(qtbot, ventana):
    ventana.load_clips([_clip(0, "/cam/A.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0])

    ventana._on_bin_quitado("Sony")

    assert ventana.clips == []
    assert ventana.bins.nombres() == []
    assert ventana.current_index == 0


def test_quitar_un_bin_que_no_existe_no_hace_nada(qtbot, ventana):
    ventana.load_clips([_clip(0, "/cam/A.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0])

    ventana._on_bin_quitado("Fantasma")

    assert len(ventana.clips) == 1


def test_el_menu_de_proxies_llama_al_bin_que_se_toco(qtbot, ventana, monkeypatch):
    ventana.load_clips([_clip(0, "/dron/D.MP4")])
    ventana.bins.agregar("Dron", Path("/dron"), [0])
    ventana._refresh_sheet()
    llamados = []
    monkeypatch.setattr(ventana, "adjuntar_proxies_de_bin", llamados.append)

    ventana.clip_sheet.bin_header_widget("Dron").proxies_requested.emit("Dron")

    assert llamados == ["Dron"]


def test_quitar_proxies_desde_el_menu_llega_a_la_ventana(qtbot, ventana, monkeypatch):
    ventana.load_clips([_clip(0, "/dron/D.MP4")])
    ventana.bins.agregar("Dron", Path("/dron"), [0])
    ventana._refresh_sheet()
    llamados = []
    monkeypatch.setattr(ventana, "quitar_proxies_de_bin", llamados.append)

    ventana.clip_sheet.bin_header_widget("Dron").proxies_cleared.emit("Dron")

    assert llamados == ["Dron"]


def test_seleccionar_el_bin_desde_el_menu_selecciona_sus_clips(qtbot, ventana):
    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/dron/D.MP4"),
                        _clip(2, "/dron/E.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0])
    ventana.bins.agregar("Dron", Path("/dron"), [1, 2])
    ventana._refresh_sheet()

    ventana.clip_sheet.bin_header_widget("Dron").select_all_requested.emit("Dron")

    assert ventana.clip_sheet.selected_indices() == [1, 2]


def test_quitar_del_proyecto_desde_el_menu_llega_a_la_ventana(qtbot, ventana):
    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/dron/D.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0])
    ventana.bins.agregar("Dron", Path("/dron"), [1])
    ventana._refresh_sheet()

    ventana.clip_sheet.bin_header_widget("Sony").remove_requested.emit("Sony")

    assert [c.ruta for c in ventana.clips] == [Path("/dron/D.MP4")]


def test_renombrar_desde_el_menu_llega_a_la_ventana(qtbot, ventana):
    ventana.load_clips([_clip(0, "/dron/D.MP4")])
    ventana.bins.agregar("Dron", Path("/dron"), [0])
    ventana._refresh_sheet()

    ventana.clip_sheet.bin_header_widget("Dron").rename_requested.emit(
        "Dron", "Dron DJI")

    assert ventana.bins.nombres() == ["Dron DJI"]


# --- lo que queda en vuelo cuando quitas un bin ------------------------------


def _png(tmp_path: Path, nombre: str) -> Path:
    """Un PNG de verdad: `QPixmap` de un archivo inventado sale nulo, y una
    miniatura nula no prueba nada."""
    from PySide6.QtGui import QPixmap
    from PySide6.QtCore import Qt

    pm = QPixmap(32, 18)
    pm.fill(Qt.GlobalColor.red)
    ruta = tmp_path / nombre
    pm.save(str(ruta))
    return ruta


def test_quitar_un_bin_invalida_las_portadas_en_vuelo(qtbot, ventana, tmp_path):
    """El fallo que la Regla 1 de `ClipSheet` existe para evitar.

    Sacar 12 cuadros de un clip tarda; quitar un bin es un clic. Un trabajo
    lanzado ANTES de quitar entrega con su indice VIEJO, y despues de quitar
    un bin de adelante ese indice es otro clip -- la miniatura del clip
    borrado aterriza sobre la tarjeta de otro.
    """
    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/cam/B.MP4"),
                        _clip(2, "/dron/D.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0, 1])
    ventana.bins.agregar("Dron", Path("/dron"), [2])
    en_vuelo = ventana._thumb_generation

    ventana._on_bin_quitado("Sony")
    ventana._on_thumbnail_ready(en_vuelo, 0, [_png(tmp_path, "a.png")])

    assert not ventana.clip_sheet.item_widgets[0].has_pixmap()


def test_quitar_un_bin_invalida_los_sondeos_de_proxy_en_vuelo(qtbot, ventana):
    """Correr `_proxy_generacion_de` conserva el VALOR, y todos los clips de
    una tanda comparten generacion: un resultado en vuelo con indice viejo
    cae sobre un indice nuevo que tiene esa misma generacion y pasa la
    guarda. Ahi `_el_proxy_calza` valida el candidato de un clip con la info
    del archivo de otro -- y entre dos tomas de la misma camara y duracion
    calza, asi que se engancha un proxy ajeno sin haber validado nada.
    """
    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/cam/B.MP4"),
                        _clip(2, "/dron/D.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0, 1])
    ventana.bins.agregar("Dron", Path("/dron"), [2])
    ventana._clip_durations = {0: 10.0, 1: 10.0, 2: 10.0}
    ventana._clip_sizes = {i: (1920, 1080) for i in range(3)}
    ventana._clip_rotations = {i: 0 for i in range(3)}
    ventana._proxy_candidatos = {2: Path("/dron/D_px.MP4")}
    ventana._proxy_generation = 5
    ventana._proxy_generacion_de = {2: 5}

    ventana._on_bin_quitado("Sony")
    # el resultado del clip 2 llega tarde, con su indice viejo
    ventana._on_proxy_sondeado(5, 2, {"fps": 30.0, "duration_frames": 300,
                                      "width": 960, "height": 540, "rotation": 0})

    assert ventana._proxy_generacion_de == {}
    assert ventana._proxy_generation > 5
    assert ventana.clips[0].ruta_proxy is None
    assert ventana._proxy_sizes == {}


def test_quitar_un_bin_de_adelante_corre_el_clip_actual(qtbot, ventana):
    """Recortar con `min` no alcanza: si lo que se fue estaba ANTES del clip
    actual, el indice tiene que bajar tantos lugares como quitados haya por
    debajo. Con `min` te quedas mirando OTRO clip sin que nadie te avise."""
    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/cam/B.MP4"),
                        _clip(2, "/dron/D.MP4"), _clip(3, "/dron/E.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0, 1])
    ventana.bins.agregar("Dron", Path("/dron"), [2, 3])
    ventana.select_clip(2)

    ventana._on_bin_quitado("Sony")

    assert ventana.current_index == 0
    assert ventana.current_clip.ruta == Path("/dron/D.MP4")


def test_si_quitas_el_bin_del_clip_actual_el_indice_no_se_pasa_del_final(qtbot, ventana):
    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/dron/D.MP4"),
                        _clip(2, "/dron/E.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0])
    ventana.bins.agregar("Dron", Path("/dron"), [1, 2])
    ventana.select_clip(2)

    ventana._on_bin_quitado("Dron")

    assert ventana.current_index == 0
    assert ventana.current_clip.ruta == Path("/cam/A.MP4")


def test_vaciar_el_proyecto_apaga_el_video(qtbot, ventana):
    """Sin esto, quitas el unico bin, la hoja queda vacia y el visor sigue
    mostrando --y reproduciendo-- un clip que ya no esta en el proyecto."""
    # a modo clip: en la hoja el clip se abre pausado a proposito, y este
    # test necesita que ESTE sonando para probar que se calla
    ventana.alternar_modo_hoja()
    ventana.load_clips([_clip(0, "/cam/A.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0])
    assert not ventana.video_widget.player.is_paused

    ventana._on_bin_quitado("Sony")

    assert ventana.video_widget.player.is_paused
    assert ("stop",) in ventana.video_widget.player._mpv.commands
    assert not ventana._auto_reproduciendo


# --- «Quitar del proyecto» pregunta antes ------------------------------------


def _responder(monkeypatch, respuesta):
    """Doble del cartel de confirmacion. Devuelve las llamadas para poder
    mirar QUE se le dijo a Bruno, no solo que se le pregunto algo."""
    from PySide6.QtWidgets import QMessageBox

    llamadas = []

    def falso(_padre, titulo, texto, *a, **k):
        llamadas.append((titulo, texto))
        return respuesta

    monkeypatch.setattr(QMessageBox, "question", falso)
    return llamadas


def test_quitar_un_bin_pregunta_antes(qtbot, ventana, monkeypatch):
    """Es la unica accion destructiva del programa y esta pegada a
    «Colapsar» en el mismo menu. Se lleva los clips con su clasificacion Y
    el historial, asi que `⌘Z` tampoco la deshace."""
    from PySide6.QtWidgets import QMessageBox

    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/cam/B.MP4"),
                        _clip(2, "/dron/D.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0, 1])
    ventana.bins.agregar("Dron", Path("/dron"), [2])
    llamadas = _responder(monkeypatch, QMessageBox.StandardButton.Yes)

    ventana._on_bin_quitado("Sony")

    assert len(llamadas) == 1
    _, texto = llamadas[0]
    assert "Sony" in texto and "2" in texto
    assert "disco" in texto  # que NO se borra nada del disco
    assert len(ventana.clips) == 1


def test_decir_que_no_deja_todo_como_estaba(qtbot, ventana, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/dron/D.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0])
    ventana.bins.agregar("Dron", Path("/dron"), [1])
    _responder(monkeypatch, QMessageBox.StandardButton.No)

    ventana._on_bin_quitado("Sony")

    assert len(ventana.clips) == 2
    assert ventana.bins.nombres() == ["Sony", "Dron"]


def test_la_ventana_le_pasa_la_resolucion_del_proxy_al_encabezado(qtbot, ventana):
    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/cam/B.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0, 1])
    ventana.clips[0].ruta_proxy = Path("/cam/A_S03.MP4")
    ventana._proxy_sizes = {0: (1920, 1080)}

    ventana._refresh_sheet()

    insignia = ventana.clip_sheet.bin_header_widget("Sony").proxy_badge
    assert insignia.text() == "proxy 1080p · 1/2"


def test_con_dos_resoluciones_en_el_mismo_bin_no_se_dice_ninguna(qtbot, ventana):
    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/cam/B.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0, 1])
    ventana.clips[0].ruta_proxy = Path("/cam/A_S03.MP4")
    ventana.clips[1].ruta_proxy = Path("/cam/B_S03.MP4")
    ventana._proxy_sizes = {0: (1920, 1080), 1: (1280, 720)}

    ventana._refresh_sheet()

    insignia = ventana.clip_sheet.bin_header_widget("Sony").proxy_badge
    assert insignia.text() == "proxy · 2/2"


def test_la_resolucion_de_un_bin_no_se_contagia_del_otro(qtbot, ventana):
    """El bug que este proyecto ya tuvo con los proxies: la Sony y el dron
    tienen su propio patron y su propia resolucion, y mezclarlos es como
    empezo todo esto."""
    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/dron/D.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0])
    ventana.bins.agregar("Dron", Path("/dron"), [1])
    ventana.clips[0].ruta_proxy = Path("/cam/A_S03.MP4")
    ventana.clips[1].ruta_proxy = Path("/dron/D_px.MP4")
    ventana._proxy_sizes = {0: (1920, 1080), 1: (1280, 720)}

    ventana._refresh_sheet()

    hoja = ventana.clip_sheet
    assert hoja.bin_header_widget("Sony").proxy_badge.text() == "proxy 1080p · 1/1"
    assert hoja.bin_header_widget("Dron").proxy_badge.text() == "proxy 720p · 1/1"


def test_renombrar_desde_la_ventana_conserva_el_bin_colapsado(qtbot, ventana):
    ventana.load_clips([_clip(0, "/dron/D.MP4")])
    ventana.bins.agregar("Dron", Path("/dron"), [0])
    ventana._refresh_sheet()
    ventana.clip_sheet.set_bin_collapsed("Dron", True)

    ventana._on_bin_renombrado("Dron", "Dron DJI")

    assert ventana.clip_sheet.bin_collapsed("Dron DJI")


def test_renombrar_a_media_generacion_de_proxies_no_pierde_la_tanda(
        qtbot, ventana, monkeypatch):
    """La tanda se acuerda del bin POR NOMBRE.

    Sin mover la llave le seguia hablando a un bin que ya no existe: la
    insignia dejaba de moverse, el menu volvia a ofrecer «Crear proxies» en
    vez de cancelar, y al cerrar la tanda nadie le pedia las portadas a esos
    clips -- que se quedaban grises esperando algo que ya no iba a llegar.
    """
    from clasificador_video.ui.main_window import _ThumbnailJob

    ventana.load_clips([_clip(0, "/dron/A.MP4"), _clip(1, "/dron/B.MP4")])
    ventana.bins.agregar("Dron", Path("/dron"), [0, 1])
    ventana._clip_durations = {0: 1.0, 1: 1.0}
    ventana._refresh_sheet()
    # nada de ffmpeg de verdad: solo interesa que la tanda quede armada
    monkeypatch.setattr(ventana._generacion_pool, "start", lambda *a, **k: None)
    ventana.generar_proxies_de_bin("Dron", preguntar=False)
    generacion = ventana._generando_proxies["generacion"]

    ventana._on_bin_renombrado("Dron", "DJI Mini")

    assert ventana._generando_proxies["bin"] == "DJI Mini"
    # y el encabezado nuevo nace ya diciendo lo que esta pasando
    assert ventana.clip_sheet.bin_header_widget("DJI Mini").proxy_badge.text() \
        == "creando proxies · 0/2"

    pedidas = []
    monkeypatch.setattr(
        ventana._thread_pool, "start",
        lambda job, *a, **k: pedidas.append(job.index)
        if isinstance(job, _ThumbnailJob) else None,
    )
    ventana._on_proxy_generado(generacion, 0, None, "")
    ventana._on_proxy_generado(generacion, 1, None, "")

    assert ventana._generando_proxies is None
    assert sorted(pedidas) == [0, 1]


# --- el encabezado pegado y la ventana ---------------------------------------


def _pegar_encabezado(qtbot, ventana, nombre):
    """Deja la hoja desplazada hasta que el flotante sea el de `nombre`."""
    ventana.resize(1000, 420)
    ventana.show()
    # NO se llama a `alternar_modo_hoja`: desde la F7 la app ya arranca en
    # la hoja, y llamarlo aqui la SACABA -- todo este bloque corria con la
    # hoja angosta del modo clip en vez de a pantalla completa, que es
    # donde el encabezado pegado tiene sentido.
    assert ventana._modo_hoja
    hoja = ventana.clip_sheet
    barra = hoja._scroll.verticalScrollBar()
    qtbot.waitUntil(lambda: barra.maximum() > 0, timeout=2000)
    # Se espera a que la geometria DEJE de moverse. El area de scroll acomoda
    # su contenido en varias vueltas encadenadas, asi que `maximum() > 0`
    # solo dice que empezo: desplazarse ahi es desplazarse sobre un contenido
    # que todavia va por la mitad. Es la misma espera que usa la hoja de
    # verdad antes de medir donde cayo una tarjeta (`_asentar_geometria`), y
    # por eso se usa ESA y no una copia -- una copia se queda vieja.
    hoja._asentar_geometria()
    # Justo despues del encabezado que se quiere pegar, no hasta el fondo:
    # abajo del todo estas en el ULTIMO bin, asi que pedir «Sony» con un
    # «Dron» debajo devolvia Dron. Funcionaba de casualidad, mientras el bin
    # pedido fuera el ultimo o el contenido no llegara tan abajo.
    cabecera = hoja.bin_header_widget(nombre)
    assert cabecera is not None, f"no hay encabezado de «{nombre}»"
    barra.setValue(cabecera.y() + 1)
    assert hoja._pegado.nombre == nombre
    return hoja._pegado


def test_el_menu_del_encabezado_pegado_llega_a_la_ventana_UNA_vez(qtbot, ventana,
                                                                  monkeypatch):
    """El flotante es una copia del encabezado del bin en el que estas, y
    reenvia lo suyo al de verdad. Justamente por eso la ventana NO lo
    conecta: si lo conectara ademas, cada renglon de su menu se ejecutaria
    dos veces -- y «Quitar del proyecto» dos veces no es un ruido, es otro
    bin menos.
    """
    ventana.load_clips([_clip(i, f"/dron/D{i}.MP4") for i in range(14)])
    ventana.bins.agregar("Dron", Path("/dron"), list(range(14)))
    ventana._refresh_sheet()
    pegado = _pegar_encabezado(qtbot, ventana, "Dron")
    llamados = []
    monkeypatch.setattr(ventana, "adjuntar_proxies_de_bin", llamados.append)

    pegado.proxies_requested.emit("Dron")

    assert llamados == ["Dron"]


def test_quitar_desde_el_encabezado_pegado_quita_una_sola_vez(qtbot, ventana,
                                                              monkeypatch):
    """El caso que de verdad duele si se ejecutara dos veces.

    Se cuentan las LLAMADAS y no el resultado: la segunda no encontraria
    el bin y se iria callada, asi que mirar los clips que quedan no
    distingue una ejecucion de dos.
    """
    ventana.load_clips([_clip(i, f"/cam/A{i}.MP4") for i in range(14)]
                       + [_clip(14, "/dron/D.MP4"), _clip(15, "/dron/E.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), list(range(14)))
    ventana.bins.agregar("Dron", Path("/dron"), [14, 15])
    ventana._refresh_sheet()
    pegado = _pegar_encabezado(qtbot, ventana, "Sony")
    llamados = []
    monkeypatch.setattr(ventana, "_on_bin_quitado", llamados.append)

    pegado.remove_requested.emit("Sony")

    assert llamados == ["Sony"]


def test_renombrar_desde_el_encabezado_pegado_llega_una_sola_vez(qtbot, ventana):
    """Con dos ejecuciones la segunda pediria renombrar «Dron», que ya no
    existe -- se traga en silencio, pero el bug seguiria ahi."""
    ventana.load_clips([_clip(i, f"/dron/D{i}.MP4") for i in range(14)])
    ventana.bins.agregar("Dron", Path("/dron"), list(range(14)))
    ventana._refresh_sheet()
    pegado = _pegar_encabezado(qtbot, ventana, "Dron")
    avisos = []
    ventana.bins.renombrar = lambda *a: avisos.append(a)

    pegado.rename_requested.emit("Dron", "Dron DJI")

    assert avisos == [("Dron", "Dron DJI")]


def test_vaciar_el_proyecto_no_enciende_un_reproductor_que_no_existia(qtbot):
    """`VideoWidget.player` se construye perezosamente porque crear un mpv
    abre hilos de verdad. Cerrar el clip cuando no hay ninguno abierto no
    puede ser justamente lo que lo encienda: una ventana sin material
    terminaba con un mpv vivo por el solo hecho de quedarse vacia.
    """
    from clasificador_video.rooms import RoomSelection

    # con el doble aunque el test sea justamente sobre NO encender el
    # reproductor: si el test fallara, sin esto encenderia un mpv de verdad
    ventana = MainWindow(project_name="Casa Jardin", room_selection=RoomSelection(),
                         video_factory=FakeMpv)
    qtbot.addWidget(ventana)

    ventana.load_clips([])

    assert ventana.video_widget._player is None


# --- arrastrar material a la hoja (F5) -------------------------------------


def test_soltar_sobre_un_bin_importa_a_ese_bin(qtbot, ventana, monkeypatch):
    """La hoja solo dice DONDE se solto. Leer disco, descartar lo que ya
    esta y avisar cuando no hay video es de `importar_rutas`, que ya existe
    -- duplicar esa logica aqui seria tener dos reglas de importacion."""
    ventana.load_clips([_clip(0, "/dron/D.MP4")])
    ventana.bins.agregar("Dron", Path("/dron"), [0])
    vistos = []
    monkeypatch.setattr(
        ventana, "importar_rutas",
        lambda rutas, nombre_de_bin=None, origen=None: vistos.append(
            (rutas, nombre_de_bin)
        ),
    )

    ventana.clip_sheet.soltado_en_bin.emit("Dron", [Path("/dron/E.MP4")])

    assert vistos == [([Path("/dron/E.MP4")], "Dron")]


def test_soltar_en_el_vacio_importa_sin_bin_y_nace_uno_nuevo(qtbot, ventana,
                                                             monkeypatch):
    vistos = []
    monkeypatch.setattr(
        ventana, "importar_rutas",
        lambda rutas, nombre_de_bin=None, origen=None: vistos.append(
            (rutas, nombre_de_bin)
        ),
    )

    ventana.clip_sheet.soltado_en_nuevo_bin.emit([Path("/dron/E.MP4")])

    assert vistos == [([Path("/dron/E.MP4")], None)]


def test_soltar_algo_que_ya_esta_importado_no_agrega_nada(qtbot, ventana,
                                                          tmp_path, monkeypatch):
    """Lo filtra `importar_rutas`: soltar dos veces la misma tarjeta no
    puede dejar cada plano duplicado."""
    from PySide6.QtWidgets import QMessageBox

    archivo = tmp_path / "A.MP4"
    archivo.touch()
    ventana.importar_rutas([archivo])
    assert len(ventana.clips) == 1
    # el aviso de «ya están en el proyecto» es modal y colgaria la suite
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)

    ventana.clip_sheet.soltado_en_nuevo_bin.emit([archivo])

    assert len(ventana.clips) == 1
    assert ventana.bins.nombres() == [tmp_path.name]


def test_soltar_algo_que_no_es_video_no_deja_un_bin_vacio(qtbot, ventana,
                                                          tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    notas = tmp_path / "notas.txt"
    notas.touch()
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)

    ventana.clip_sheet.soltado_en_nuevo_bin.emit([notas])

    assert ventana.bins.nombres() == []
    assert ventana.clips == []


# --- filtrar por bin (F6) --------------------------------------------------


def test_filtrar_por_bin_acota_la_cola_de_las_flechas(qtbot, ventana):
    """Los filtros de esta app no cambian solo lo que ves: cambian por
    donde se mueven las flechas. El de bin no es la excepcion."""
    from clasificador_video.filters import FilterState

    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/dron/D.MP4"),
                        _clip(2, "/dron/E.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0])
    ventana.bins.agregar("Dron", Path("/dron"), [1, 2])

    ventana.set_filters(FilterState(bin="Dron"))

    assert ventana.queue() == [1, 2]


def test_el_chip_de_bin_de_la_hoja_llega_hasta_la_cola(qtbot, ventana):
    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/dron/D.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0])
    ventana.bins.agregar("Dron", Path("/dron"), [1])
    ventana._refresh_sheet()

    ventana.clip_sheet.chip_de_bin("Dron").click()

    assert ventana.queue() == [1]


def test_el_visor_dice_de_que_bin_es_el_clip_actual(qtbot, ventana):
    # a modo clip: desde la F7 la app arranca en la hoja, y ahi los overlays
    # del visor no se refrescan porque no hay «clip actual» que describir
    ventana.alternar_modo_hoja()
    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/dron/D.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0])
    ventana.bins.agregar("Dron", Path("/dron"), [1])

    ventana.select_clip(1)

    assert "Dron" in ventana.video_stage.bin_label.text()


# --- renombrar desde el teclado de verdad (revision final) -----------------


def test_renombrar_con_la_tecla_enter_no_destruye_el_campo_bajo_los_pies(
        qtbot, ventana):
    """El encabezado viejo se destruye DENTRO del evento de teclado de su
    propio `QLineEdit`.

    `_confirmar_nombre` corre dentro de `returnPressed`, emite
    `rename_requested`, y eso termina en `_sincronizar_encabezados`, que ya
    no encuentra el nombre viejo y le saca el padre al encabezado -- con su
    `name_edit` adentro -- mientras el stack de C++ sigue dentro de
    `QLineEdit::keyPressEvent`. Use-after-free.

    Emitir `returnPressed` desde Python NO lo ve: ahi no hay ningun frame de
    C++ al que volver. Por eso este test manda la tecla de verdad.
    """
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    ventana.load_clips([_clip(0, "/dron/D.MP4")])
    ventana.bins.agregar("Dron", Path("/dron"), [0])
    ventana._refresh_sheet()
    ventana.show()
    qtbot.waitExposed(ventana)
    cabecera = ventana.clip_sheet.bin_header_widget("Dron")
    cabecera.empezar_a_renombrar()
    cabecera.name_edit.setText("Dron DJI")

    QTest.keyClick(cabecera.name_edit, Qt.Key.Key_Return)
    qtbot.wait(10)

    assert ventana.bins.nombres() == ["Dron DJI"]
    assert ventana.clip_sheet.bin_headers() == ["Dron DJI"]


def test_renombrar_desde_el_menu_no_destruye_el_menu_bajo_los_pies(qtbot, ventana):
    """El mismo camino, pero disparado desde el `QAction` del menu: ahi
    ademas se suelta `self._menu` desde adentro de su propio `triggered`."""
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    ventana.load_clips([_clip(0, "/dron/D.MP4")])
    ventana.bins.agregar("Dron", Path("/dron"), [0])
    ventana._refresh_sheet()
    ventana.show()
    qtbot.waitExposed(ventana)
    cabecera = ventana.clip_sheet.bin_header_widget("Dron")
    menu = cabecera.construir_menu()
    cabecera._menu = menu

    menu.actions()[0].trigger()      # «Renombrar bin…»
    cabecera.name_edit.setText("Dron DJI")
    QTest.keyClick(cabecera.name_edit, Qt.Key.Key_Return)
    qtbot.wait(10)

    assert ventana.bins.nombres() == ["Dron DJI"]


def test_quitar_el_bin_que_estabas_filtrando_recrea_las_tarjetas_UNA_vez(
        qtbot, ventana):
    """`set_bin_order` corre desde `_refresh_sheet` y, al desaparecer el bin
    filtrado, la hoja avisa que el filtro volvio a «todos». Ese aviso
    reentra a `_refresh_sheet` antes de que el de afuera actualice las
    tarjetas, y quedaban DOS `set_clips` seguidos: destruir y recrear las
    132 tarjetas dos veces, en la unica operacion destructiva de la app y
    en el terreno donde ya hubo segfaults.
    """
    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/dron/D.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0])
    ventana.bins.agregar("Dron", Path("/dron"), [1])
    ventana._refresh_sheet()
    ventana.clip_sheet.chip_de_bin("Dron").click()
    veces = []
    original = ventana.clip_sheet.set_clips
    ventana.clip_sheet.set_clips = lambda thumbs: (veces.append(len(thumbs)),
                                                   original(thumbs))[1]

    ventana._on_bin_quitado("Dron")

    assert len(veces) == 1
    assert ventana.filters.bin == "todos"


# --- F8 Tarea 4: el boton «+ Bin nuevo» --------------------------------------


def test_crear_un_bin_lo_deja_listo_para_recibir_clips(qtbot, ventana):
    ventana.load_clips([_clip(0, "/cam/A.MP4")])

    ventana._on_bin_nuevo_pedido()

    assert "Bin" in ventana.bins.nombres()[-1]
    assert ventana.clip_sheet.bin_headers()[-1] == ventana.bins.nombres()[-1]


def test_el_bin_nuevo_nace_con_el_nombre_en_edicion(qtbot, ventana):
    """Ponerle nombre es parte de crearlo, no un segundo paso que haya que
    recordar."""
    ventana.load_clips([_clip(0, "/cam/A.MP4")])

    ventana._on_bin_nuevo_pedido()

    cabecera = ventana.clip_sheet.bin_header_widget(ventana.bins.nombres()[-1])
    assert not cabecera.name_edit.isHidden()
    assert cabecera.name_label.isHidden()


def test_dos_bins_nuevos_no_se_pisan_el_nombre(qtbot, ventana):
    ventana.load_clips([_clip(0, "/cam/A.MP4")])

    ventana._on_bin_nuevo_pedido()
    ventana._on_bin_nuevo_pedido()

    assert ventana.bins.nombres() == ["Bin", "Bin 2"]


def test_el_bin_nuevo_se_guarda(qtbot, tmp_path, ventana):
    ventana.session_path = tmp_path / "sesion.json"
    ventana.load_clips([_clip(0, "/cam/A.MP4")])

    ventana._on_bin_nuevo_pedido()
    ventana._write_autosave_now()
    assert ventana._autosave_pool.waitForDone(2000)

    data = json.loads((ventana.session_path).read_text())
    assert data["bins"][-1]["clips"] == []


def test_el_boton_de_la_hoja_llega_hasta_la_ventana(qtbot, ventana):
    """La señal de la hoja tiene que estar enchufada: sin esto el boton se
    ve, se aprieta y no pasa nada."""
    ventana.load_clips([_clip(0, "/cam/A.MP4")])

    ventana.clip_sheet.boton_bin_nuevo.click()

    assert ventana.bins.nombres() == ["Bin"]


# --- soltar material sobre la seccion «Sin bin» -----------------------------


def test_soltar_en_sin_bin_no_crea_ningun_bin(qtbot, ventana, tmp_path,
                                              monkeypatch):
    """El bug: el nombre de la SECCION viajaba como nombre de bin, y nacia
    un bin de verdad llamado «Sin bin» -- con su chip de filtro, su lugar en
    el autosave y un «Quitar del proyecto» que ya si borraba clips."""
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.extract_thumbnail_strip",
        lambda *a, **k: [],
    )
    archivo = tmp_path / "A.MP4"
    archivo.touch()

    ventana.clip_sheet.soltado_sin_bin.emit([archivo])

    assert ventana.bins.nombres() == []
    assert len(ventana.clips) == 1
    assert ventana.bins.bin_de(0) is None


def test_importar_suelto_deja_los_clips_en_la_seccion_de_sueltos(qtbot, ventana,
                                                                 tmp_path,
                                                                 monkeypatch):
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.extract_thumbnail_strip",
        lambda *a, **k: [],
    )
    carpeta = _carpeta_con(tmp_path, "FX30", "C0001.MP4")

    ventana.importar_rutas([carpeta], sueltos=True)

    assert ventana.bins.nombres() == []
    assert ventana.clip_sheet.bin_headers() == [SIN_BIN]


def test_importar_suelto_sobre_material_que_ya_tiene_bins_no_toca_esos_bins(
        qtbot, ventana, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.extract_thumbnail_strip",
        lambda *a, **k: [],
    )
    sony = _carpeta_con(tmp_path, "FX30", "C0001.MP4")
    ventana.importar_rutas([sony])
    suelto = tmp_path / "S.MP4"
    suelto.touch()

    ventana.importar_rutas([suelto], sueltos=True)

    assert ventana.bins.nombres() == ["FX30"]
    assert ventana.bins.clips_de("FX30") == [0]
    assert ventana.bins.bin_de(1) is None


def test_seleccionar_los_clips_de_sin_bin_selecciona_los_sueltos(qtbot, ventana):
    """El renglon promete «Seleccionar los N clips» con el numero real. Antes
    `bins.clips_de("Sin bin")` devolvia [] y el menu terminaba
    DESELECCIONANDO todo lo que tuvieras marcado: prometia N y hacia lo
    contrario."""
    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/cam/B.MP4"),
                        _clip(2, "/cam/C.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [1])
    ventana._refresh_sheet()

    ventana._on_bin_seleccionado(SIN_BIN)

    assert ventana.clip_sheet.selected_indices() == [0, 2]


def test_la_seccion_de_sueltos_muestra_los_proxies_de_sus_clips(qtbot, ventana):
    """El proxy es del CLIP, no del bin (spec §6.b): un clip suelto puede
    tenerlo enganchado. `_refrescar_meta_de_bins` solo recorria
    `bins.nombres()`, asi que «Sin bin» decia siempre «sin proxies» aunque
    sus clips tuvieran uno."""
    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/cam/B.MP4")])
    ventana.clips[0].ruta_proxy = Path("/cam/AS03.MP4")
    ventana._proxy_sizes[0] = (1920, 1080)

    ventana._refresh_sheet()

    insignia = ventana.clip_sheet.bin_header_widget(SIN_BIN).proxy_badge
    assert insignia.text() == "proxy 1080p · 1/2"


def test_la_seccion_de_sueltos_no_dice_de_que_carpeta_salio(qtbot, ventana):
    """No salio de ninguna: son los clips que no pertenecen a nadie."""
    ventana.load_clips([_clip(0, "/cam/A.MP4")])

    ventana._refresh_sheet()

    assert ventana.clip_sheet.bin_header_widget(SIN_BIN).source_label.text() == ""


# --- arrastrar clips de un bin a otro (F9) ---------------------------------


def test_mover_clips_cambia_el_bin_y_nada_mas(qtbot, ventana):
    """Lo que hace barata esta operacion: no toca indices, asi que no hay
    que correr proxies, duraciones ni historial.
    """
    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/cam/B.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0, 1])
    ventana.bins.crear_vacio("Dron")
    ventana.clips[0].ruta_proxy = Path("/cam/AS03.MP4")
    ventana._proxy_sizes[0] = (1080, 1920)
    ventana.clips[0].categoria_path = ["Cocina"]

    ventana._on_clips_movidos([0], "Dron")

    assert ventana.bins.bin_de(0) == "Dron"
    assert ventana.bins.bin_de(1) == "Sony"                       # el otro no
    assert ventana.clips[0].ruta_proxy == Path("/cam/AS03.MP4")   # se lo lleva
    assert ventana._proxy_sizes[0] == (1080, 1920)
    assert ventana.clips[0].categoria_path == ["Cocina"]          # el cuarto no se toca
    assert ventana.clips[0].orden == 1                            # ni el orden


def test_mover_clips_a_sin_bin_los_deja_sueltos(qtbot, ventana):
    """«Sin bin» no es un bin: el destino que llega es `None` y el clip
    queda sin pertenecer a ninguno."""
    ventana.load_clips([_clip(0, "/cam/A.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0])

    ventana._on_clips_movidos([0], None)

    assert ventana.bins.bin_de(0) is None
    assert ventana.bins.clips_de("Sony") == []


def test_mover_clips_se_guarda_solo(qtbot, tmp_path, ventana):
    """Si no se guardara, reabrir el proyecto te devolveria los clips al bin
    del que los sacaste."""
    ventana.session_path = tmp_path / "sesion.json"
    ventana.load_clips([_clip(0, "/cam/A.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0])
    ventana.bins.crear_vacio("Dron")

    ventana._on_clips_movidos([0], "Dron")

    # el guardado es con debounce: mover pide guardar, no escribe en el acto.
    # Primero se comprueba que lo PIDIO --que es lo que hace este handler-- y
    # despues se fuerza la escritura para mirar lo que quedo en el archivo.
    assert ventana._autosave_timer.isActive()
    ventana._write_autosave_now()
    assert ventana._autosave_pool.waitForDone(2000)

    datos = json.loads((tmp_path / "sesion.json").read_text())
    guardados = {b["nombre"]: b["clips"] for b in datos["bins"]}
    assert guardados["Dron"] == [0]
    assert guardados["Sony"] == []


def test_mover_varios_clips_de_golpe(qtbot, ventana):
    ventana.load_clips([_clip(i, f"/cam/{i}.MP4") for i in range(3)])
    ventana.bins.agregar("Sony", Path("/cam"), [0, 1, 2])
    ventana.bins.crear_vacio("Dron")

    ventana._on_clips_movidos([0, 2], "Dron")

    assert ventana.bins.clips_de("Dron") == [0, 2]
    assert ventana.bins.clips_de("Sony") == [1]


def test_soltar_en_el_cuarto_de_otro_bin_no_reclasifica(qtbot, ventana):
    """Decision de Bruno: arrastrar es para acomodar por camara. El cuarto
    se sigue poniendo con el teclado -- un arrastre mal soltado no puede
    cambiarte el dato que mas trabajo cuesta.
    """
    ventana.load_clips([_clip(0, "/cam/A.MP4"), _clip(1, "/dron/B.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0])
    ventana.bins.agregar("Dron", Path("/dron"), [1])
    ventana.clips[0].categoria_path = ["Cocina"]
    ventana.clips[1].categoria_path = ["Recamara"]

    # soltado encima del subgrupo «Recamara» del Dron
    ventana._on_clips_movidos([0], "Dron")

    assert ventana.bins.bin_de(0) == "Dron"
    assert ventana.clips[0].categoria_path == ["Cocina"]


def test_la_hoja_no_se_reconstruye_al_mover(qtbot, ventana):
    """Reconstruir tiraria las portadas ya generadas -- que es justo el bug
    que Bruno reporto al importar una segunda carpeta."""
    ventana.load_clips([_clip(0, "/cam/A.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0])
    ventana.bins.crear_vacio("Dron")
    llamadas = []
    ventana._refresh_sheet = lambda force_rebuild=False: llamadas.append(force_rebuild)

    ventana._on_clips_movidos([0], "Dron")

    assert llamadas == [False]


def test_el_aviso_de_quitar_un_bin_de_un_clip_no_dice_1_clips(qtbot, ventana,
                                                              monkeypatch):
    ventana.load_clips([_clip(0, "/cam/A.MP4")])
    ventana.bins.agregar("Sony", Path("/cam"), [0])
    textos = []

    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(
        QMessageBox, "question",
        lambda *a, **k: (textos.append(a[2]), QMessageBox.StandardButton.No)[1],
    )

    ventana._on_bin_quitado("Sony")

    assert "Se va su clip" in textos[0]
    assert "1 clips" not in textos[0]


def test_soltar_dos_carpetas_a_la_vez_deja_el_origen_en_el_padre_comun(
        qtbot, tmp_path, monkeypatch, ventana):
    """El origen se tomaba del padre del PRIMER archivo, asi que todo lo
    demas quedaba colgando de una carpeta que no lo contiene."""
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.extract_thumbnail_strip", lambda *a, **k: []
    )
    disco = tmp_path / "DISCO"
    disco.mkdir()
    sony = _carpeta_con(disco, "tarjeta1", "C0001.MP4")
    dron = _carpeta_con(disco, "tarjeta2", "C0002.MP4")

    ventana.importar_rutas([sony, dron], nombre_de_bin="Rodaje")

    assert ventana.bins.origen_de("Rodaje") == disco


def test_soltar_dos_carpetas_a_la_vez_deja_a_todos_los_clips_con_relativa(
        qtbot, tmp_path, monkeypatch, ventana):
    """LA comprobacion: sin ruta relativa no hay como reencontrar el clip en
    otra computadora, y sin este arreglo la mitad se quedaba sin ella."""
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.extract_thumbnail_strip", lambda *a, **k: []
    )
    disco = tmp_path / "DISCO"
    disco.mkdir()
    sony = _carpeta_con(disco, "tarjeta1", "C0001.MP4", "C0002.MP4")
    dron = _carpeta_con(disco, "tarjeta2", "DJI_0001.MP4")

    ventana.importar_rutas([sony, dron], nombre_de_bin="Rodaje")

    relativas = rutas_relativas(ventana.clips, ventana.bins)
    assert sorted(relativas.values()) == [
        "tarjeta1/C0001.MP4", "tarjeta1/C0002.MP4", "tarjeta2/DJI_0001.MP4",
    ]
    assert len(relativas) == len(ventana.clips)


def test_dos_carpetas_de_discos_distintos_no_suben_el_origen_a_la_raiz(
        qtbot, tmp_path, monkeypatch, ventana):
    """Ahi el ancestro comun seria el disco entero, y reencontrar tendria que
    recorrerlo completo: se conserva la carpeta del primero, que es el
    comportamiento de siempre."""
    monkeypatch.setattr(
        "clasificador_video.ui.main_window.extract_thumbnail_strip", lambda *a, **k: []
    )
    # `tmp_path` hace de raiz de disco: las dos tarjetas cuelgan de ella y
    # su ancestro comun es justo lo que la guarda no deja tomar. Se parchea
    # el dato y no la funcion, para que corra el camino de verdad.
    monkeypatch.setattr("clasificador_video.bins.RAICES_DEMASIADO_ARRIBA",
                        frozenset({tmp_path}))
    sony = _carpeta_con(tmp_path, "CARD_A", "C0001.MP4")
    dron = _carpeta_con(tmp_path, "CARD_B", "C0002.MP4")

    ventana.importar_rutas([sony, dron], nombre_de_bin="Rodaje")

    assert ventana.bins.origen_de("Rodaje") == sony


# ---------------------------------------------------------------------------
# Los bins en el deshacer
# (spec 2026-08-18-bins-en-el-deshacer-design.md)
# ---------------------------------------------------------------------------


def _ventana_con_bins(qtbot) -> MainWindow:
    """Tres clips en «Card A» y un «Card B» vacío al lado.

    No usa la fixture `ventana` porque estas pruebas asignan cuartos con el
    teclado, y aquella nace con la lista de cuartos vacía.
    """
    seleccion = RoomSelection()
    for cuarto in ("Sala", "Cocina"):
        seleccion.add(cuarto)
    window = MainWindow(project_name="Casa Jardin", room_selection=seleccion,
                        video_factory=FakeMpv)
    window._probe_clip = _probe_falso
    qtbot.addWidget(window)
    window.resize(1500, 900)
    window.load_clips([_clip(i, f"/x/C{i:04d}.MP4") for i in range(3)])
    window.bins.agregar("Card A", Path("/A"), [0, 1, 2])
    window.bins.crear_vacio("Card B")
    window._refresh_sheet(force_rebuild=True)
    window.show()
    qtbot.waitExposed(window)
    if window._modo_hoja:
        window.alternar_modo_hoja()
    return window


def test_deshacer_un_arrastre_devuelve_el_clip_a_su_bin(qtbot):
    """El bug que originó todo esto, medido el 2026-08-18: arrastras un clip
    a otro bin, aprietas ⌘Z, y el clip se quedaba donde lo soltaste MIENTRAS
    otro clip perdía el cuarto que le habías puesto."""
    window = _ventana_con_bins(qtbot)
    window.select_clip(0)
    window.handle_key_press("1")               # Sala al clip 1
    window.select_clip(2)
    window.handle_key_press("2")               # Cocina al clip 3

    window._on_clips_movidos([0], "Card B")
    window.undo()

    assert window.bins.bin_de(0) == "Card A"
    assert window.clips[2].categoria_path == ["Cocina"]


def test_deshacer_un_arrastre_devuelve_cada_clip_a_SU_bin(qtbot):
    """Varios clips de bins distintos en el mismo gesto: cada uno vuelve a
    donde estaba, no todos al primero."""
    window = _ventana_con_bins(qtbot)
    window.bins.mover([2], "Card B")           # el clip 3 ya vivía en Card B

    window._on_clips_movidos([0, 2], None)     # los dos, a «Sin bin»
    window.undo()

    assert window.bins.bin_de(0) == "Card A"
    assert window.bins.bin_de(2) == "Card B"


def test_deshacer_devuelve_a_sin_bin_al_que_venia_suelto(qtbot):
    """«Suelto» es un estado valido, no la ausencia de dato: devolverlo al
    primer bin seria inventarle una camara."""
    window = _ventana_con_bins(qtbot)
    window.bins.mover([1], None)               # el clip 2 queda suelto

    window._on_clips_movidos([1], "Card B")
    window.undo()

    assert window.bins.bin_de(1) is None


def test_deshacer_un_arrastre_no_toca_el_cuarto_ni_el_estado(qtbot):
    """Arrastrar cambia el bin y nada mas; deshacerlo, tambien. Es lo que
    hace que ⌘Z se pueda apretar sin pensarlo."""
    window = _ventana_con_bins(qtbot)
    window.select_clip(0)
    window.handle_key_press("1")               # Sala
    window.select_clip(0)
    window.handle_key_press("p")               # pick
    window.handle_key_press("i")               # in

    window._on_clips_movidos([0], "Card B")
    window.undo()

    assert window.clips[0].categoria_path == ["Sala"]
    assert window.clips[0].flag == "pick"
    assert window.clips[0].in_frame is not None


def test_el_arrastre_deja_su_renglon_en_el_historial(qtbot):
    window = _ventana_con_bins(qtbot)

    window._on_clips_movidos([0, 1], "Card B")

    entrada = window.history.entries()[0]
    assert entrada.etiqueta == "Card B"
    assert entrada.detalle == "→ 2 clips"
    assert entrada.bins_antes == {0: "Card A", 1: "Card A"}


def test_deshacer_un_arrastre_no_mete_su_propia_entrada(qtbot):
    """Si `_on_clips_movidos` registrara desde adentro, deshacer meteria una
    entrada nueva y ⌘Z se volveria un columpio: dos teclazos y vuelves al
    principio sin haber deshecho nada."""
    window = _ventana_con_bins(qtbot)
    window._on_clips_movidos([0], "Card B")
    cuantas = len(window.history.entries())

    window.undo()

    assert len(window.history.entries()) == cuantas - 1


def test_deshacer_quita_el_bin_recien_creado(qtbot):
    window = _ventana_con_bins(qtbot)
    antes = window.bins.nombres()

    window._on_bin_nuevo_pedido()
    assert len(window.bins.nombres()) == len(antes) + 1
    window.undo()

    assert window.bins.nombres() == antes


def test_crear_un_bin_deja_su_renglon(qtbot):
    window = _ventana_con_bins(qtbot)

    window._on_bin_nuevo_pedido()

    entrada = window.history.entries()[0]
    assert entrada.bin_creado in window.bins.nombres()
    assert entrada.detalle == "→ bin nuevo"


def test_no_se_borra_un_bin_que_ya_tiene_clips(qtbot):
    """El arrastre fue una decision aparte y mas reciente: borrar el bin se
    llevaria dos cosas de un click. Primero deshaces el arrastre --que desde
    hoy se puede-- y luego el bin."""
    window = _ventana_con_bins(qtbot)
    window._on_bin_nuevo_pedido()
    nuevo = window.history.entries()[0].bin_creado
    window._on_clips_movidos([0], nuevo)

    window.undo()          # deshace el ARRASTRE, que es lo de arriba
    window.undo()          # y ahora si, el bin

    assert nuevo not in window.bins.nombres()
    assert window.bins.bin_de(0) == "Card A"


def test_deshacer_un_renombrado_recupera_el_nombre_viejo(qtbot):
    window = _ventana_con_bins(qtbot)

    window._on_bin_renombrado("Card A", "Camara 1")
    assert "Camara 1" in window.bins.nombres()
    window.undo()

    assert "Card A" in window.bins.nombres()
    assert "Camara 1" not in window.bins.nombres()
    assert window.bins.bin_de(0) == "Card A"


def test_renombrar_un_bin_arregla_los_renglones_viejos(qtbot):
    """Un renglon que hable de un bin que ya no existe promete devolver algo
    inalcanzable. Mismo arreglo que ya se le hizo a los cuartos."""
    window = _ventana_con_bins(qtbot)
    window._on_clips_movidos([0], "Card B")

    window._on_bin_renombrado("Card A", "Camara 1")

    movido = [e for e in window.history.entries() if e.bins_antes][0]
    assert movido.bins_antes == {0: "Camara 1"}


def test_renombrar_un_bin_no_toca_el_renglon_de_un_cuarto_que_se_llame_igual(qtbot):
    """Un cuarto «Cocina» y una camara «Cocina» pueden convivir."""
    window = _ventana_con_bins(qtbot)
    window.select_clip(0)
    window.handle_key_press("2")                    # Cocina, el CUARTO
    window._on_bin_renombrado("Card A", "Cocina")   # y ahora el BIN

    window._on_bin_renombrado("Cocina", "Camara 1")

    de_cuarto = [e for e in window.history.entries() if not e.habla_de_bins()][0]
    assert de_cuarto.etiqueta == "Cocina"


def test_el_renglon_del_bin_creado_se_bloquea_al_meterle_clips(qtbot):
    window = _ventana_con_bins(qtbot)
    window._on_bin_nuevo_pedido()
    entrada = window.history.entries()[0]
    nuevo = entrada.bin_creado
    assert window._motivo_bloqueado(entrada) is None

    window._on_clips_movidos([0], nuevo)

    assert window._motivo_bloqueado(entrada) == "ya tiene clips"


def test_se_bloquea_el_arrastre_cuyo_bin_de_origen_ya_no_esta(qtbot):
    window = _ventana_con_bins(qtbot)
    window._on_clips_movidos([0], "Card B")
    entrada = window.history.entries()[0]
    window.bins.quitar("Card A")

    assert window._motivo_bloqueado(entrada) == "ese bin ya no está"


def test_cmd_z_no_salta_al_siguiente_cuando_el_de_arriba_esta_bloqueado(qtbot):
    """Es el bug entero, en chico: si ⌘Z se saltara el renglon bloqueado
    desharia una accion anterior sin decirlo -- exactamente lo que este
    trabajo existe para quitar."""
    window = _ventana_con_bins(qtbot)
    window.select_clip(0)
    window.handle_key_press("1")                 # Sala, y entra al historial
    window._on_bin_nuevo_pedido()
    nuevo = window.history.entries()[0].bin_creado
    window.bins.mover([1], nuevo)                # a mano: no crea entrada
    window._refresh_history()

    window.undo()

    assert window.clips[0].categoria_path == ["Sala"]
    assert nuevo in window.bins.nombres()
    # y el renglon SIGUE ahi: sin esto la prueba pasa por el motivo
    # equivocado. `⌘Z` se tragaba la entrada bloqueada --la sacaba de la
    # pila-- y nada mas: no pasaba nada visible, pero el renglon
    # desaparecia del rail y la siguiente vez ⌘Z si deshacia el cuarto.
    assert [e.bin_creado for e in window.history.entries()] == [nuevo, None]


def test_el_boton_de_deshacer_se_apaga_si_el_de_arriba_esta_bloqueado(qtbot):
    window = _ventana_con_bins(qtbot)
    window._on_bin_nuevo_pedido()
    nuevo = window.history.entries()[0].bin_creado
    assert window.tool_column.undo_button.isEnabled()

    window.bins.mover([1], nuevo)
    window._refresh_history()

    assert not window.tool_column.undo_button.isEnabled()
