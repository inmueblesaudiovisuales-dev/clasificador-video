# tests/test_ingest.py
from pathlib import Path

from clasificador_video.ingest import IngestTree, archivos_de_video


def test_importar_una_carpeta_la_agrega_con_su_nombre(tmp_path):
    origen = tmp_path / "FX30"
    origen.mkdir()
    (origen / "C0001.MP4").touch()
    (origen / "C0002.MP4").touch()

    tree = IngestTree()
    tree.import_folder(origen)

    assert [f.name for f in tree.top_level_folders()] == ["FX30"]
    assert {p.name for p in tree.top_level_folders()[0].files} == {"C0001.MP4", "C0002.MP4"}


def test_importar_varias_carpetas_a_la_vez(tmp_path):
    fx30 = tmp_path / "FX30"
    dron = tmp_path / "Dron"
    fx30.mkdir()
    dron.mkdir()
    (fx30 / "C0001.MP4").touch()
    (dron / "DJI_0001.MP4").touch()

    tree = IngestTree()
    tree.import_folders([fx30, dron])

    names = {f.name for f in tree.top_level_folders()}
    assert names == {"FX30", "Dron"}


def test_importar_solo_lee_archivos_de_video_no_otros_archivos(tmp_path):
    origen = tmp_path / "FX30"
    origen.mkdir()
    (origen / "C0001.MP4").touch()
    (origen / "notas.txt").touch()
    (origen / ".DS_Store").touch()

    tree = IngestTree()
    tree.import_folder(origen)

    assert [p.name for p in tree.top_level_folders()[0].files] == ["C0001.MP4"]


def test_renombrar_carpeta_top_level(tmp_path):
    origen = tmp_path / "FX30"
    origen.mkdir()

    tree = IngestTree()
    tree.import_folder(origen)
    tree.rename_folder(origen, "Cámara principal")

    assert tree.top_level_folders()[0].display_name == "Cámara principal"


def test_un_proxy_dentro_de_la_carpeta_importada_no_entra_como_clip(tmp_path):
    """Si el `S03` entra como material, Bruno ve 256 clips donde hay 128
    -- y clasifica dos veces el mismo plano sin darse cuenta."""
    origen = tmp_path / "FX30"
    origen.mkdir()
    (origen / "C0001.MP4").touch()
    (origen / "C0001S03.MP4").touch()

    tree = IngestTree()
    tree.import_folder(origen)

    assert [p.name for p in tree.top_level_folders()[0].files] == ["C0001.MP4"]


def test_archivos_de_video_acepta_carpetas_y_sueltos_mezclados(tmp_path):
    carpeta = tmp_path / "cam"
    carpeta.mkdir()
    (carpeta / "A.MP4").touch()
    (carpeta / "AS03.MP4").touch()      # proxy de camara: NO es material
    (carpeta / "notas.txt").touch()
    suelto = tmp_path / "B.MOV"
    suelto.touch()

    assert archivos_de_video([carpeta, suelto]) == [carpeta / "A.MP4", suelto]


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
