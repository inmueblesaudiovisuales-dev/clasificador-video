"""Descubrimiento de carpetas de cámara para la importación rápida."""
from pathlib import Path

from clasificador_video import importacion_rapida


def _armar_proyecto(tmp_path: Path, *, con_pocket: bool = True) -> Path:
    proyecto = tmp_path / "IAV-2609.10-A"
    assets = proyecto / "01. ASSETS VIDEO"
    (assets / "01. VIDEOS SONY").mkdir(parents=True)
    (assets / "02. VIDEO DRONE").mkdir(parents=True)
    (assets / "04. VIDEOS OSMO ACTION").mkdir(parents=True)
    proxies = assets / "07. PROXIES"
    (proxies / "01. PROXY SONY").mkdir(parents=True)
    (proxies / "02. PROXY DRONE").mkdir(parents=True)
    if con_pocket:
        (assets / "03. VIDEOS OSMO POCKET").mkdir(parents=True)
    return proyecto


def test_encuentra_sony_y_dron(tmp_path):
    proyecto = _armar_proyecto(tmp_path)
    resultado = importacion_rapida.detectar_carpetas_de_material(proyecto)
    assert resultado.sony == proyecto / "01. ASSETS VIDEO" / "01. VIDEOS SONY"
    assert resultado.dron == proyecto / "01. ASSETS VIDEO" / "02. VIDEO DRONE"
    assert resultado.faltantes == ()


def test_encuentra_pocket_cuando_existe(tmp_path):
    proyecto = _armar_proyecto(tmp_path, con_pocket=True)
    resultado = importacion_rapida.detectar_carpetas_de_material(proyecto)
    assert resultado.pocket == (
        proyecto / "01. ASSETS VIDEO" / "03. VIDEOS OSMO POCKET")


def test_pocket_ausente_no_es_un_faltante(tmp_path):
    proyecto = _armar_proyecto(tmp_path, con_pocket=False)
    resultado = importacion_rapida.detectar_carpetas_de_material(proyecto)
    assert resultado.pocket is None
    assert "Pocket" not in resultado.faltantes
    assert resultado.faltantes == ()


def test_osmo_action_nunca_se_reconoce_como_pocket_ni_como_nada(tmp_path):
    proyecto = _armar_proyecto(tmp_path, con_pocket=False)
    resultado = importacion_rapida.detectar_carpetas_de_material(proyecto)
    carpeta_action = proyecto / "01. ASSETS VIDEO" / "04. VIDEOS OSMO ACTION"
    assert resultado.pocket != carpeta_action
    assert resultado.sony != carpeta_action
    assert resultado.dron != carpeta_action


def test_no_confunde_la_carpeta_de_proxies_con_la_de_material(tmp_path):
    """`01. PROXY SONY` también dice "sony" en el nombre, pero vive DENTRO
    de `07. PROXIES` -- un nivel más abajo de lo que se recorre."""
    proyecto = _armar_proyecto(tmp_path)
    resultado = importacion_rapida.detectar_carpetas_de_material(proyecto)
    assert resultado.sony.name == "01. VIDEOS SONY"
    assert "PROXY" not in resultado.sony.name.upper()


def test_falta_sony_y_dron_se_avisa(tmp_path):
    proyecto = tmp_path / "IAV-2609.10-A"
    (proyecto / "01. ASSETS VIDEO").mkdir(parents=True)
    resultado = importacion_rapida.detectar_carpetas_de_material(proyecto)
    assert resultado.sony is None
    assert resultado.dron is None
    assert set(resultado.faltantes) == {"Sony", "Drone"}


def test_sin_carpeta_de_assets_video_avisa_esa_carpeta(tmp_path):
    proyecto = tmp_path / "IAV-2609.10-A"
    proyecto.mkdir()
    resultado = importacion_rapida.detectar_carpetas_de_material(proyecto)
    assert resultado.assets_video is None
    assert resultado.faltantes == ("01. ASSETS VIDEO",)


def test_carpeta_de_proxies_en_icloud_usa_el_folio_del_nombre(tmp_path):
    proyecto = tmp_path / "material" / "IAV-2609.10-A"
    proyecto.mkdir(parents=True)
    raiz_icloud = tmp_path / "iCloud"

    destino = importacion_rapida.carpeta_de_proxies_en_icloud(
        proyecto, raiz_icloud)

    from clasificador_video import proyecto_colaborativo as pc
    esperado = pc.ruta_del_proyecto(raiz_icloud, "IAV-2609.10-A") / pc.CARPETA_PROXIES
    assert destino == esperado


def test_carpeta_de_proxies_en_icloud_sin_raiz_configurada_es_none(tmp_path):
    proyecto = tmp_path / "IAV-2609.10-A"
    proyecto.mkdir()
    assert importacion_rapida.carpeta_de_proxies_en_icloud(proyecto, None) is None


def test_carpeta_de_proxies_en_icloud_con_nombre_que_no_es_folio_es_none(tmp_path):
    proyecto = tmp_path / "Carpeta cualquiera"
    proyecto.mkdir()
    raiz_icloud = tmp_path / "iCloud"
    assert importacion_rapida.carpeta_de_proxies_en_icloud(
        proyecto, raiz_icloud) is None
