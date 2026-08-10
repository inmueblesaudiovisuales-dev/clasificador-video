# tests/ui/test_main_window_revinculo.py
"""Abrir el proyecto en otra computadora: qué se avisa y qué se reconecta.

Los tres finales de `revinculo.Reencuentro` se comprueban **por separado**,
que es como se le dicen a Bruno: reconectado, sin confirmar y no encontrado
son tres cosas distintas, y decirle «no lo encontré» cuando lo que pasó fue
que apareció el `C0001.MP4` de otra tarjeta sería mentirle.
"""
import json
from pathlib import Path

import pytest

from PySide6.QtWidgets import QWidget

from clasificador_video.manifest import Clip
from clasificador_video.rooms import RoomSelection
from clasificador_video.ui.main_window import MainWindow


class FakeMpv:
    """Mismo doble que el resto de los tests de la ventana."""

    def __init__(self, **kwargs):
        self.init_kwargs = kwargs
        self.loaded_path = None
        self.pause = True
        self.time_pos = 0.0

    def play(self, path):
        self.loaded_path = path

    def command(self, *args):
        pass


def _clip(i, ruta):
    return Clip(orden=i + 1, ruta=Path(ruta), categoria_path=[], fps=30.0)


def _probe_falso(path):
    return {"fps": 30.0, "duration_frames": 300, "width": 1920,
            "height": 1080, "rotation": 0}


@pytest.fixture
def ventana(qtbot):
    window = MainWindow(project_name="Casa Jardín", room_selection=RoomSelection(),
                        video_factory=FakeMpv)
    window._probe_clip = _probe_falso
    qtbot.addWidget(window)
    return window


# ---------------------------------------------------------------- avisar


def _botones(ventana, etiqueta):
    """Cuántos botones con ese texto tiene la barra."""
    return sum(1 for b in ventana.aviso_de_media.findChildren(QWidget)
               if b.objectName() == "avisoBuscar" and b.text() == etiqueta)


def _revisar(ventana, qtbot):
    """Revisa la media y espera el resultado, que llega de otro hilo."""
    ventana.revisar_media()
    qtbot.waitUntil(lambda: ventana._revisiones_terminadas > 0, timeout=3000)


def test_revisar_no_toca_el_disco_en_el_hilo_de_la_interfaz(ventana, qtbot):
    """La lección ya estaba escrita en `proyecto.con_pesos_medidos`: un
    `stat` sobre un volumen montado e incomunicado se traba hasta el
    timeout, y son uno por clip en serie. Y esto corre al ABRIR un proyecto
    cuyo material puede estar en un disco de red que ya no responde."""
    ventana.load_clips([_clip(0, "/no/existe/A.MP4")])
    ventana.bins.agregar("Dron", Path("/no/existe"), [0])

    ventana.revisar_media()

    # todavía no sabe nada: si esto ya estuviera lleno, la revisión habría
    # corrido en el hilo de la interfaz.
    assert ventana.aviso_de_media.isHidden()
    qtbot.waitUntil(lambda: not ventana.aviso_de_media.isHidden(), timeout=3000)


def test_redibujar_la_barra_no_vuelve_a_preguntarle_al_disco(ventana, qtbot,
                                                             monkeypatch):
    """`_refrescar_aviso` corre en cada renombrado de bin y en cada
    reconexión. Barrer todos los bins otra vez cada vez es el mismo `stat`
    en serie, en el mismo hilo."""
    ventana.load_clips([_clip(0, "/no/existe/A.MP4")])
    ventana.bins.agregar("Dron", Path("/no/existe"), [0])
    _revisar(ventana, qtbot)

    def no_preguntes(*_a, **_k):
        raise AssertionError("volvió a barrer el disco")

    monkeypatch.setattr("clasificador_video.revinculo.faltantes_de", no_preguntes)
    ventana._refrescar_aviso()

    assert ventana.aviso_de_media.text() == "Dron — 1 clip no se encuentra."


def test_al_abrir_avisa_cuantos_faltan_por_bin(ventana, qtbot):
    ventana.load_clips([_clip(0, "/no/existe/A.MP4"), _clip(1, "/no/existe/B.MP4")])
    ventana.bins.agregar("Dron", Path("/no/existe"), [0, 1])

    _revisar(ventana, qtbot)

    assert not ventana.aviso_de_media.isHidden()
    assert ventana.aviso_de_media.text() == "Dron — 2 clips no se encuentran."


def test_un_solo_clip_faltante_se_dice_en_singular(ventana, qtbot):
    ventana.load_clips([_clip(0, "/no/existe/A.MP4")])
    ventana.bins.agregar("Dron", Path("/no/existe"), [0])

    _revisar(ventana, qtbot)

    assert ventana.aviso_de_media.text() == "Dron — 1 clip no se encuentra."


def test_avisa_de_cada_bin_por_separado(ventana, qtbot):
    ventana.load_clips([_clip(0, "/dron/A.MP4"), _clip(1, "/sony/B.MP4"),
                        _clip(2, "/sony/C.MP4")])
    ventana.bins.agregar("Dron", Path("/dron"), [0])
    ventana.bins.agregar("Sony FX30", Path("/sony"), [1, 2])

    _revisar(ventana, qtbot)

    assert ventana.aviso_de_media.text().splitlines() == [
        "Dron — 1 clip no se encuentra.",
        "Sony FX30 — 2 clips no se encuentran.",
    ]


def test_con_toda_la_media_en_su_lugar_no_hay_aviso(ventana, tmp_path, qtbot):
    archivo = tmp_path / "A.MP4"
    archivo.write_bytes(b"x" * 500)
    ventana.load_clips([_clip(0, archivo)])
    ventana.bins.agregar("Dron", tmp_path, [0])

    _revisar(ventana, qtbot)

    assert ventana.aviso_de_media.isHidden()
    assert ventana.aviso_de_media.text() == ""


# ------------------------------------------------------------ reconectar


def _proyecto_con_un_clip_perdido(ventana, tmp_path, qtbot, peso_en_disco):
    """Un bin de un clip cuyo archivo se movió a `nueva/`."""
    nueva = tmp_path / "nueva"
    nueva.mkdir()
    (nueva / "A.MP4").write_bytes(b"x" * peso_en_disco)
    ventana.session_path = tmp_path / "P.cvproj"
    ventana.load_clips([_clip(0, "/viejo/A.MP4")])
    ventana.bins.agregar("Dron", Path("/viejo"), [0])
    ventana._bytes_guardados = {0: 500}
    ventana._relativas = {0: "A.MP4"}
    ventana._clip_durations = {0: 10.0}   # 10 s a 30 fps = 300 cuadros
    _revisar(ventana, qtbot)
    return nueva


def test_reconectar_reescribe_las_rutas_y_guarda(ventana, tmp_path, qtbot):
    nueva = _proyecto_con_un_clip_perdido(ventana, tmp_path, qtbot, peso_en_disco=500)

    ventana.reconectar_bin("Dron", nueva)

    assert ventana.clips[0].ruta == nueva / "A.MP4"
    assert ventana.bins.origen_de("Dron") == nueva
    # y queda guardado, para que la próxima vez abra sin preguntar
    ventana._flush_autosave()
    data = json.loads((tmp_path / "P.cvproj").read_text())
    assert data["clips"][0]["ruta"] == str(nueva / "A.MP4")
    assert data["bins"][0]["origen"] == str(nueva)


def test_reconectar_lo_dice_y_deja_de_pedir_buscar(ventana, tmp_path, qtbot):
    nueva = _proyecto_con_un_clip_perdido(ventana, tmp_path, qtbot, peso_en_disco=500)

    ventana.reconectar_bin("Dron", nueva)

    assert ventana.aviso_de_media.text() == "Dron — 1 clip reconectado."


def test_lo_que_no_confirma_no_se_engancha_y_se_dice(ventana, tmp_path, qtbot):
    """El caso de la segunda tarjeta de la misma cámara: mismo nombre,
    otro material."""
    nueva = _proyecto_con_un_clip_perdido(ventana, tmp_path, qtbot, peso_en_disco=111)

    ventana.reconectar_bin("Dron", nueva)

    assert ventana.clips[0].ruta == Path("/viejo/A.MP4")   # sin tocar
    assert "no coincide" in ventana.aviso_de_media.text().lower()
    assert ventana.aviso_de_media.text() == (
        "Dron — 1 clip no coincide: hay un archivo con ese nombre, pero no es "
        "el mismo video. No se conectó."
    )


def test_lo_que_no_aparece_se_dice_distinto_de_lo_que_no_coincide(ventana, tmp_path, qtbot):
    vacia = tmp_path / "vacia"
    vacia.mkdir()
    ventana.session_path = tmp_path / "P.cvproj"
    ventana.load_clips([_clip(0, "/viejo/A.MP4")])
    ventana.bins.agregar("Dron", Path("/viejo"), [0])
    ventana._bytes_guardados = {0: 500}
    ventana._relativas = {0: "A.MP4"}
    _revisar(ventana, qtbot)

    ventana.reconectar_bin("Dron", vacia)

    assert ventana.clips[0].ruta == Path("/viejo/A.MP4")
    assert ventana.aviso_de_media.text() == (
        "Dron — 1 clip no apareció en esa carpeta."
    )


def test_los_finales_van_en_renglones_aparte(ventana, tmp_path, qtbot):
    """Reconectado, sin confirmar y no encontrado no se mezclan en una sola
    frase: son tres cosas distintas y cada una se dice con sus palabras."""
    nueva = tmp_path / "nueva"
    nueva.mkdir()
    (nueva / "A.MP4").write_bytes(b"x" * 500)   # calza
    (nueva / "B.MP4").write_bytes(b"x" * 111)   # el tocayo de otra tarjeta
    # de C.MP4 no hay nada
    ventana.session_path = tmp_path / "P.cvproj"
    ventana.load_clips([_clip(0, "/viejo/A.MP4"), _clip(1, "/viejo/B.MP4"),
                        _clip(2, "/viejo/C.MP4")])
    ventana.bins.agregar("Dron", Path("/viejo"), [0, 1, 2])
    ventana._bytes_guardados = {0: 500, 1: 500, 2: 500}
    ventana._relativas = {0: "A.MP4", 1: "B.MP4", 2: "C.MP4"}
    _revisar(ventana, qtbot)

    ventana.reconectar_bin("Dron", nueva)

    assert ventana.aviso_de_media.text().splitlines() == [
        "Dron — 1 clip reconectado.",
        "Dron — 1 clip no coincide: hay un archivo con ese nombre, pero no es "
        "el mismo video. No se conectó.",
        "Dron — 1 clip no apareció en esa carpeta.",
    ]


def test_reconectar_no_mueve_indices(ventana, tmp_path, qtbot):
    """Reconectar cambia rutas, no el orden: todo lo que va indexado por
    clip tiene que seguir describiendo al mismo clip."""
    nueva = tmp_path / "nueva"
    nueva.mkdir()
    (nueva / "B.MP4").write_bytes(b"x" * 500)
    ventana.session_path = tmp_path / "P.cvproj"
    ventana.load_clips([_clip(0, "/viejo/A.MP4"), _clip(1, "/viejo/B.MP4")])
    ventana.bins.agregar("Dron", Path("/viejo"), [0, 1])
    ventana._bytes_guardados = {0: 400, 1: 500}
    ventana._relativas = {0: "A.MP4", 1: "B.MP4"}
    ventana._clip_sizes = {0: (1920, 1080), 1: (1080, 1920)}
    _revisar(ventana, qtbot)

    ventana.reconectar_bin("Dron", nueva)

    assert ventana.bins.clips_de("Dron") == [0, 1]
    assert [c.orden for c in ventana.clips] == [1, 2]
    assert ventana._clip_sizes == {0: (1920, 1080), 1: (1080, 1920)}


def test_las_portadas_se_piden_solo_de_los_reconectados(ventana, tmp_path, qtbot, monkeypatch):
    """Sin acotar, `_schedule_thumbnails()` sube la generación, invalida lo
    que está en vuelo y encola trabajos duplicados sobre el mismo socket."""
    nueva = _proyecto_con_un_clip_perdido(ventana, tmp_path, qtbot, peso_en_disco=500)
    pedidos = []
    monkeypatch.setattr(ventana, "_schedule_thumbnails",
                        lambda indices=None: pedidos.append(indices))

    ventana.reconectar_bin("Dron", nueva)

    assert pedidos == [[0]]


def test_sin_nada_reconectado_no_se_toca_el_origen_del_bin(ventana, tmp_path, qtbot):
    """Señalar la carpeta equivocada no puede borrar de dónde salió el
    material: es lo único que queda para volver a intentarlo."""
    nueva = _proyecto_con_un_clip_perdido(ventana, tmp_path, qtbot, peso_en_disco=111)

    ventana.reconectar_bin("Dron", nueva)

    assert ventana.bins.origen_de("Dron") == Path("/viejo")


def test_reconectar_a_medias_no_pierde_la_relativa_del_que_falta(ventana, tmp_path, qtbot):
    """El origen del bin pasa a ser la carpeta nueva, y la ruta relativa del
    que sigue perdido ya no se puede calcular contra ella. Si se tirara, ese
    clip se quedaría sin con qué reencontrarse nunca más."""
    nueva = tmp_path / "nueva"
    nueva.mkdir()
    (nueva / "A.MP4").write_bytes(b"x" * 500)
    ventana.session_path = tmp_path / "P.cvproj"
    ventana.load_clips([_clip(0, "/viejo/A.MP4"), _clip(1, "/viejo/B.MP4")])
    ventana.bins.agregar("Dron", Path("/viejo"), [0, 1])
    ventana._bytes_guardados = {0: 500, 1: 500}
    ventana._relativas = {0: "A.MP4", 1: "B.MP4"}
    _revisar(ventana, qtbot)

    ventana.reconectar_bin("Dron", nueva)
    ventana._flush_autosave()

    data = json.loads((tmp_path / "P.cvproj").read_text())
    assert data["relativas"] == {"0": "A.MP4", "1": "B.MP4"}

def test_lo_que_no_se_pudo_comprobar_no_se_dice_como_que_no_coincide(
        ventana, tmp_path, qtbot):
    """El archivo apareció y el proyecto no guardó ni peso ni duración: no
    hay CON QUÉ comprobarlo. Decir «no es el mismo video» sería afirmar una
    comparación que nunca se hizo."""
    nueva = tmp_path / "nueva"
    nueva.mkdir()
    (nueva / "A.MP4").write_bytes(b"x" * 500)
    ventana.session_path = tmp_path / "P.cvproj"
    ventana.load_clips([_clip(0, "/viejo/A.MP4")])
    ventana.bins.agregar("Dron", Path("/viejo"), [0])
    ventana._relativas = {0: "A.MP4"}       # sin pesos ni duraciones
    _revisar(ventana, qtbot)

    ventana.reconectar_bin("Dron", nueva)

    assert ventana.clips[0].ruta == Path("/viejo/A.MP4")
    assert ventana.aviso_de_media.text() == (
        "Dron — 1 clip apareció, pero el proyecto no guardó su peso ni su "
        "duración, así que no hay con qué comprobar que sea el mismo. No se "
        "conectó."
    )


def test_dos_clips_que_se_pelean_un_archivo_no_se_dicen_como_impostores(
        ventana, tmp_path, qtbot):
    """Aquí el archivo SÍ calzaba con los dos. «No es el mismo video» sería
    mentira: lo es, y por eso justamente no se sabe de cuál."""
    nueva = tmp_path / "nueva"
    (nueva / "sobrevivio").mkdir(parents=True)
    (nueva / "sobrevivio" / "C0001.MP4").write_bytes(b"x" * 500)
    ventana.session_path = tmp_path / "P.cvproj"
    ventana.load_clips([_clip(0, "/viejo/t1/C0001.MP4"),
                        _clip(1, "/viejo/t2/C0001.MP4")])
    ventana.bins.agregar("Sony", Path("/viejo"), [0, 1])
    ventana._bytes_guardados = {0: 500, 1: 500}
    ventana._relativas = {0: "t1/C0001.MP4", 1: "t2/C0001.MP4"}
    _revisar(ventana, qtbot)

    ventana.reconectar_bin("Sony", nueva)

    assert ventana.clips[0].ruta == Path("/viejo/t1/C0001.MP4")
    assert ventana.aviso_de_media.text() == (
        "Sony — 2 clips se pelean el mismo archivo: hay uno solo con ese "
        "nombre y los dos lo reclaman. Ninguno se conectó."
    )


def test_un_clip_sin_ruta_relativa_se_dice_que_no_se_puede_buscar(
        ventana, tmp_path, qtbot):
    """Ese clip no se buscó: no hay con qué buscarlo. Decirle «no apareció
    en esa carpeta» esconde que está perdido para siempre."""
    nueva = tmp_path / "nueva"
    nueva.mkdir()
    ventana.session_path = tmp_path / "P.cvproj"
    ventana.load_clips([_clip(0, "/viejo/A.MP4")])
    ventana.bins.agregar("Dron", Path("/viejo"), [0])
    ventana._bytes_guardados = {0: 500}
    ventana._relativas = {}                 # sin relativa
    _revisar(ventana, qtbot)

    ventana.reconectar_bin("Dron", nueva)

    assert ventana.aviso_de_media.text() == (
        "Dron — 1 clip no se puede buscar: el proyecto no guardó de dónde "
        "colgaba dentro de su carpeta."
    )


def test_un_solo_boton_de_buscar_por_bin(ventana, tmp_path, qtbot):
    """Dos «Buscar…» idénticos en el mismo bin hacen exactamente lo mismo."""
    nueva = tmp_path / "nueva"
    nueva.mkdir()
    (nueva / "A.MP4").write_bytes(b"x" * 111)   # tocayo: no coincide
    ventana.session_path = tmp_path / "P.cvproj"
    ventana.load_clips([_clip(0, "/viejo/A.MP4"), _clip(1, "/viejo/B.MP4")])
    ventana.bins.agregar("Dron", Path("/viejo"), [0, 1])
    ventana._bytes_guardados = {0: 500, 1: 500}
    ventana._relativas = {0: "A.MP4", 1: "B.MP4"}
    _revisar(ventana, qtbot)

    ventana.reconectar_bin("Dron", nueva)

    assert len(ventana.aviso_de_media.text().splitlines()) == 2
    assert _botones(ventana, "Buscar…") == 1


def test_el_renglon_verde_se_va_solo(ventana, tmp_path, qtbot):
    """«1 clip reconectado» no puede quedarse el resto de la sesión
    robándole alto al video por algo que ya salió bien."""
    nueva = _proyecto_con_un_clip_perdido(ventana, tmp_path, qtbot,
                                          peso_en_disco=500)
    ventana.reconectar_bin("Dron", nueva)
    assert ventana.aviso_de_media.text() == "Dron — 1 clip reconectado."

    ventana._olvidar_exitos()

    assert ventana.aviso_de_media.isHidden()
    assert ventana.aviso_de_media.text() == ""


# ---------------------------------------------------------------- proxies


def test_reconectar_tambien_engancha_el_proxy(ventana, tmp_path, qtbot):
    """Sin esto, después de reconectar en la otra computadora todo el
    proyecto navega sobre el 4K HEVC: 530 ms por cuadro contra 22."""
    nueva = tmp_path / "nueva"
    nueva.mkdir()
    (nueva / "A.MP4").write_bytes(b"x" * 500)
    (nueva / "AS03.MP4").write_bytes(b"x" * 50)
    ventana.session_path = tmp_path / "P.cvproj"
    clip = _clip(0, "/viejo/A.MP4")
    clip.ruta_proxy = Path("/viejo/proxy/AS03.MP4")
    ventana.load_clips([clip])
    ventana.bins.agregar("Dron", Path("/viejo"), [0])
    ventana._bytes_guardados = {0: 500}
    ventana._relativas = {0: "A.MP4"}
    _revisar(ventana, qtbot)

    ventana.reconectar_bin("Dron", nueva)

    assert ventana._proxy_candidatos.get(0) == nueva / "AS03.MP4"
    assert "sin proxy" not in ventana.aviso_de_media.text()


def test_el_proxy_viejo_no_se_queda_apuntando_a_la_nada(ventana, tmp_path, qtbot):
    """La portada se extrae del proxy si lo hay. Dejar el candidato viejo
    apuntando a una ruta muerta deja la tarjeta sin portada y sin
    explicación."""
    nueva = _proyecto_con_un_clip_perdido(ventana, tmp_path, qtbot,
                                          peso_en_disco=500)
    ventana.clips[0].ruta_proxy = Path("/viejo/proxy/AS03.MP4")
    ventana._proxy_candidatos = {0: Path("/viejo/proxy/AS03.MP4")}
    ventana._proxy_sizes = {0: (1280, 720)}

    ventana.reconectar_bin("Dron", nueva)

    assert 0 not in ventana._proxy_candidatos
    assert 0 not in ventana._proxy_sizes
    assert ventana.clips[0].ruta_proxy is None


def test_si_el_proxy_no_aparece_se_dice_y_se_puede_buscar(ventana, tmp_path, qtbot):
    """«Que quede reconectado o que se diga que quedó sin proxy.»"""
    nueva = _proyecto_con_un_clip_perdido(ventana, tmp_path, qtbot,
                                          peso_en_disco=500)
    ventana.clips[0].ruta_proxy = Path("/viejo/proxy/AS03.MP4")

    ventana.reconectar_bin("Dron", nueva)

    assert ventana.aviso_de_media.text().splitlines()[-1] == (
        "Dron — 1 clip quedó sin proxy: vas a navegar sobre el original, que "
        "es mucho más lento."
    )
    assert _botones(ventana, "Buscar proxies…") == 1


def test_buscar_los_proxies_aparte_los_engancha(ventana, tmp_path, qtbot):
    """El proxy vive en su propia carpeta, al lado de la de clips."""
    nueva = _proyecto_con_un_clip_perdido(ventana, tmp_path, qtbot,
                                          peso_en_disco=500)
    aparte = tmp_path / "proxies"
    aparte.mkdir()
    (aparte / "AS03.MP4").write_bytes(b"x" * 50)
    ventana.clips[0].ruta_proxy = Path("/viejo/proxy/AS03.MP4")
    ventana.reconectar_bin("Dron", nueva)

    ventana.reconectar_proxies_de_bin("Dron", aparte)

    assert ventana._proxy_candidatos.get(0) == aparte / "AS03.MP4"
    assert "sin proxy" not in ventana.aviso_de_media.text()


def test_en_solo_video_la_barra_no_reaparece(ventana, qtbot):
    """La regla de visibilidad la tiene la ventana, que es la única que sabe
    del modo solo video (el widget no lo sabe: ver
    `test_el_widget_nunca_se_muestra_ni_se_esconde_solo`)."""
    ventana.load_clips([_clip(0, "/no/existe/A.MP4")])
    ventana.bins.agregar("Dron", Path("/no/existe"), [0])
    ventana.alternar_solo_video()
    assert ventana._solo_video

    _revisar(ventana, qtbot)

    assert ventana.aviso_de_media.tiene_avisos()
    assert ventana.aviso_de_media.isHidden()

    ventana.alternar_solo_video()

    assert not ventana.aviso_de_media.isHidden()
