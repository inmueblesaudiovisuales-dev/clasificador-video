# tests/test_ingest.py
from pathlib import Path

from clasificador_video.ingest import IngestTree


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
