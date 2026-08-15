# tests/test_ingest.py
from pathlib import Path

from clasificador_video.ingest import archivos_de_video


def test_archivos_de_video_acepta_carpetas_y_sueltos_mezclados(tmp_path):
    carpeta = tmp_path / "cam"
    carpeta.mkdir()
    (carpeta / "A.MP4").touch()
    (carpeta / "AS03.MP4").touch()      # proxy de camara: NO es material
    (carpeta / "notas.txt").touch()
    suelto = tmp_path / "B.MOV"
    suelto.touch()

    assert archivos_de_video([carpeta, suelto]) == [carpeta / "A.MP4", suelto]


def test_un_proxy_terminado_en_proxy_no_entra_como_material(tmp_path):
    """`C0001_proxy.MP4` junto a su original duplicaba la toma, igual que
    pasaba con los `S03` de la Sony y con los `.LRF` del dron."""
    (tmp_path / "C0001.MP4").touch()
    (tmp_path / "C0001_proxy.MP4").touch()
    (tmp_path / "C0002_PROXY.MOV").touch()      # tambien en mayusculas

    assert archivos_de_video([tmp_path]) == [tmp_path / "C0001.MP4"]


def test_un_clip_que_solo_dice_proxy_en_medio_si_es_material(tmp_path):
    """Se mira el FINAL del nombre, no si la palabra aparece: un recorrido
    llamado `proxy_casa.MP4` es material."""
    (tmp_path / "proxy_casa.MP4").touch()

    assert archivos_de_video([tmp_path]) == [tmp_path / "proxy_casa.MP4"]


def test_archivos_de_video_no_repite(tmp_path):
    (tmp_path / "A.MP4").touch()

    assert archivos_de_video([tmp_path, tmp_path / "A.MP4"]) == [tmp_path / "A.MP4"]


def test_archivos_de_video_no_baja_a_las_subcarpetas(tmp_path):
    """Mismo criterio que `import_folders`: arrastrar una tarjeta de camara
    no puede traerse sus carpetas de sistema."""
    (tmp_path / "A.MP4").touch()
    adentro = tmp_path / "PRIVATE"
    adentro.mkdir()
    (adentro / "B.MP4").touch()

    assert archivos_de_video([tmp_path]) == [tmp_path / "A.MP4"]


def test_archivos_de_video_descarta_lo_que_no_existe(tmp_path):
    """`is_dir()` da False para algo que no existe, asi que una ruta muerta
    con sufijo de video se colaba como archivo -- y el aviso que salia
    despues era «falta ffprobe», el diagnostico equivocado."""
    assert archivos_de_video([tmp_path / "fantasma.MP4"]) == []


def test_archivos_de_video_junta_varias_carpetas_en_orden(tmp_path):
    """Lo que hacia `import_folders`: dos tarjetas de camara de un jalon,
    cada una con sus archivos y en el orden en que las diste."""
    fx30 = tmp_path / "FX30"
    dron = tmp_path / "Dron"
    fx30.mkdir()
    dron.mkdir()
    (fx30 / "C0001.MP4").touch()
    (dron / "DJI_0001.MP4").touch()

    assert archivos_de_video([fx30, dron]) == [
        fx30 / "C0001.MP4", dron / "DJI_0001.MP4",
    ]


def test_archivos_de_video_ignora_los_que_no_son_video(tmp_path):
    """`.DS_Store` y las notas de produccion viven en la misma carpeta que
    el material y no son clips."""
    (tmp_path / "C0001.MP4").touch()
    (tmp_path / "notas.txt").touch()
    (tmp_path / ".DS_Store").touch()

    assert archivos_de_video([tmp_path]) == [tmp_path / "C0001.MP4"]


def test_un_proxy_de_camara_no_entra_como_clip(tmp_path):
    """Si el `S03` entra como material, Bruno ve 256 clips donde hay 128
    -- y clasifica dos veces el mismo plano sin darse cuenta."""
    (tmp_path / "C0001.MP4").touch()
    (tmp_path / "C0001S03.MP4").touch()

    assert archivos_de_video([tmp_path]) == [tmp_path / "C0001.MP4"]


def test_el_lrf_del_dron_no_entra_como_clip(tmp_path):
    """DJI escribe un `.LRF` --su propio proxy-- junto a cada `.MP4`, en la
    misma carpeta. Al arrastrar la tarjeta completa cada toma del dron
    entraba DOS veces, igual que pasaba con los `S03` de la Sony.

    No se queda como material «por si acaso»: se midio contra la carpeta
    real de Bruno y el `.LRF` NO calza cuadro a cuadro con el original --el
    contenido va corrido entre 0 y 5 cuadros, y el desfase cambia de toma
    en toma--, asi que ni siquiera sirve de proxy. Bruno lo decidio el
    2026-08-10: fuera.
    """
    (tmp_path / "DJI_0001.MP4").touch()
    (tmp_path / "DJI_0001.LRF").touch()

    assert archivos_de_video([tmp_path]) == [tmp_path / "DJI_0001.MP4"]


def test_un_lrf_solo_tampoco_entra(tmp_path):
    """Aunque no tenga su `.MP4` al lado: sigue sin poder marcarse in/out
    encima."""
    (tmp_path / "DJI_0001.LRF").touch()

    assert archivos_de_video([tmp_path]) == []
