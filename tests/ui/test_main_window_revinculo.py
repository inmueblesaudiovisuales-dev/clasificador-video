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


def test_al_abrir_avisa_cuantos_faltan_por_bin(ventana):
    ventana.load_clips([_clip(0, "/no/existe/A.MP4"), _clip(1, "/no/existe/B.MP4")])
    ventana.bins.agregar("Dron", Path("/no/existe"), [0, 1])

    ventana.revisar_media()

    assert not ventana.aviso_de_media.isHidden()
    assert ventana.aviso_de_media.text() == "Dron — 2 clips no se encuentran."


def test_un_solo_clip_faltante_se_dice_en_singular(ventana):
    ventana.load_clips([_clip(0, "/no/existe/A.MP4")])
    ventana.bins.agregar("Dron", Path("/no/existe"), [0])

    ventana.revisar_media()

    assert ventana.aviso_de_media.text() == "Dron — 1 clip no se encuentra."


def test_avisa_de_cada_bin_por_separado(ventana):
    ventana.load_clips([_clip(0, "/dron/A.MP4"), _clip(1, "/sony/B.MP4"),
                        _clip(2, "/sony/C.MP4")])
    ventana.bins.agregar("Dron", Path("/dron"), [0])
    ventana.bins.agregar("Sony FX30", Path("/sony"), [1, 2])

    ventana.revisar_media()

    assert ventana.aviso_de_media.text().splitlines() == [
        "Dron — 1 clip no se encuentra.",
        "Sony FX30 — 2 clips no se encuentran.",
    ]


def test_con_toda_la_media_en_su_lugar_no_hay_aviso(ventana, tmp_path):
    archivo = tmp_path / "A.MP4"
    archivo.write_bytes(b"x" * 500)
    ventana.load_clips([_clip(0, archivo)])
    ventana.bins.agregar("Dron", tmp_path, [0])

    ventana.revisar_media()

    assert ventana.aviso_de_media.isHidden()
    assert ventana.aviso_de_media.text() == ""


# ------------------------------------------------------------ reconectar


def _proyecto_con_un_clip_perdido(ventana, tmp_path, peso_en_disco):
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
    return nueva


def test_reconectar_reescribe_las_rutas_y_guarda(ventana, tmp_path):
    nueva = _proyecto_con_un_clip_perdido(ventana, tmp_path, peso_en_disco=500)

    ventana.reconectar_bin("Dron", nueva)

    assert ventana.clips[0].ruta == nueva / "A.MP4"
    assert ventana.bins.origen_de("Dron") == nueva
    # y queda guardado, para que la próxima vez abra sin preguntar
    ventana._flush_autosave()
    data = json.loads((tmp_path / "P.cvproj").read_text())
    assert data["clips"][0]["ruta"] == str(nueva / "A.MP4")
    assert data["bins"][0]["origen"] == str(nueva)


def test_reconectar_lo_dice_y_deja_de_pedir_buscar(ventana, tmp_path):
    nueva = _proyecto_con_un_clip_perdido(ventana, tmp_path, peso_en_disco=500)

    ventana.reconectar_bin("Dron", nueva)

    assert ventana.aviso_de_media.text() == "Dron — 1 clip reconectado."


def test_lo_que_no_confirma_no_se_engancha_y_se_dice(ventana, tmp_path):
    """El caso de la segunda tarjeta de la misma cámara: mismo nombre,
    otro material."""
    nueva = _proyecto_con_un_clip_perdido(ventana, tmp_path, peso_en_disco=111)

    ventana.reconectar_bin("Dron", nueva)

    assert ventana.clips[0].ruta == Path("/viejo/A.MP4")   # sin tocar
    assert "no coincide" in ventana.aviso_de_media.text().lower()
    assert ventana.aviso_de_media.text() == (
        "Dron — 1 clip no coincide: hay un archivo con ese nombre, pero no es "
        "el mismo video. No se conectó."
    )


def test_lo_que_no_aparece_se_dice_distinto_de_lo_que_no_coincide(ventana, tmp_path):
    vacia = tmp_path / "vacia"
    vacia.mkdir()
    ventana.session_path = tmp_path / "P.cvproj"
    ventana.load_clips([_clip(0, "/viejo/A.MP4")])
    ventana.bins.agregar("Dron", Path("/viejo"), [0])
    ventana._bytes_guardados = {0: 500}
    ventana._relativas = {0: "A.MP4"}

    ventana.reconectar_bin("Dron", vacia)

    assert ventana.clips[0].ruta == Path("/viejo/A.MP4")
    assert ventana.aviso_de_media.text() == (
        "Dron — 1 clip no apareció en esa carpeta."
    )


def test_los_tres_finales_van_en_renglones_aparte(ventana, tmp_path):
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

    ventana.reconectar_bin("Dron", nueva)

    assert ventana.aviso_de_media.text().splitlines() == [
        "Dron — 1 clip reconectado.",
        "Dron — 1 clip no coincide: hay un archivo con ese nombre, pero no es "
        "el mismo video. No se conectó.",
        "Dron — 1 clip no apareció en esa carpeta.",
    ]


def test_reconectar_no_mueve_indices(ventana, tmp_path):
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

    ventana.reconectar_bin("Dron", nueva)

    assert ventana.bins.clips_de("Dron") == [0, 1]
    assert [c.orden for c in ventana.clips] == [1, 2]
    assert ventana._clip_sizes == {0: (1920, 1080), 1: (1080, 1920)}


def test_las_portadas_se_piden_solo_de_los_reconectados(ventana, tmp_path, monkeypatch):
    """Sin acotar, `_schedule_thumbnails()` sube la generación, invalida lo
    que está en vuelo y encola trabajos duplicados sobre el mismo socket."""
    nueva = _proyecto_con_un_clip_perdido(ventana, tmp_path, peso_en_disco=500)
    pedidos = []
    monkeypatch.setattr(ventana, "_schedule_thumbnails",
                        lambda indices=None: pedidos.append(indices))

    ventana.reconectar_bin("Dron", nueva)

    assert pedidos == [[0]]


def test_sin_nada_reconectado_no_se_toca_el_origen_del_bin(ventana, tmp_path):
    """Señalar la carpeta equivocada no puede borrar de dónde salió el
    material: es lo único que queda para volver a intentarlo."""
    nueva = _proyecto_con_un_clip_perdido(ventana, tmp_path, peso_en_disco=111)

    ventana.reconectar_bin("Dron", nueva)

    assert ventana.bins.origen_de("Dron") == Path("/viejo")


def test_reconectar_a_medias_no_pierde_la_relativa_del_que_falta(ventana, tmp_path):
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

    ventana.reconectar_bin("Dron", nueva)
    ventana._flush_autosave()

    data = json.loads((tmp_path / "P.cvproj").read_text())
    assert data["relativas"] == {"0": "A.MP4", "1": "B.MP4"}
