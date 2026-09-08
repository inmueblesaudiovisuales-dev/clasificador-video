from pathlib import Path

from clasificador_video.camaras import (
    CAMARAS, DJI, OTRA, SONY, camara_de_archivo, camara_de_bin,
)


def test_un_archivo_del_dron_se_reconoce_por_su_nombre():
    assert camara_de_archivo(Path("/x/DJI_20260817182345_0081_D.MP4")) == DJI


def test_lo_que_no_dice_DJI_se_asume_sony():
    """La regla de Bruno, tal cual la dijo: «los de DJI por lo general
    tienen el nombre DJI, los que no por lo general serán sony»."""
    assert camara_de_archivo(Path("/x/20260817_PIB0016.MP4")) == SONY
    assert camara_de_archivo(Path("/x/C0001.MP4")) == SONY


def test_el_DJI_del_nombre_no_distingue_mayusculas():
    assert camara_de_archivo(Path("/x/dji_0081.mp4")) == DJI


def test_solo_cuenta_el_nombre_del_archivo_no_la_carpeta():
    """Una carpeta «02. VIDEO DRONE/DJI» con material de la Sony adentro no
    puede volver dron a esos clips: lo que identifica a la cámara es cómo
    NOMBRA ella sus archivos, no dónde los guardó Bruno."""
    assert camara_de_archivo(Path("/DJI/20260817_PIB0016.MP4")) == SONY


def test_un_bin_toma_la_camara_de_la_mayoria():
    rutas = [Path("/x/DJI_0001.MP4"), Path("/x/DJI_0002.MP4"),
             Path("/x/20260817_PIB0016.MP4")]
    assert camara_de_bin(rutas) == DJI


def test_un_empate_se_va_a_sony():
    """No hay razón para preferir el dron en un empate, y hace falta UNA
    respuesta: es la cámara con la que Bruno graba casi todo."""
    assert camara_de_bin([Path("/x/DJI_0001.MP4"), Path("/x/C0001.MP4")]) == SONY


def test_un_bin_vacio_es_sony():
    """Un bin creado con «+ Bin nuevo» todavía no tiene archivos. Tiene que
    salir con una cámara puesta igual, o el encabezado no sabría qué pintar."""
    assert camara_de_bin([]) == SONY


def test_otra_nunca_sale_de_adivinar():
    """`otra` es la válvula para una cámara que no es ninguna de las dos, y
    solo la pone Bruno a mano."""
    supuestas = [camara_de_archivo(Path(f"/x/{n}")) for n in
                 ("DJI_1.MP4", "C0001.MP4", "otra_cosa.mov", "OTRA.mp4")]
    assert OTRA not in supuestas


def test_las_camaras_validas_son_tres_y_estan_en_orden_de_menu():
    assert CAMARAS == (SONY, DJI, OTRA)
