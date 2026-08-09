# tests/test_proxy_match.py
from pathlib import Path

from clasificador_video.proxy_match import (
    PROFUNDIDAD_DE_BUSQUEDA,
    buscar_proxies,
    etiqueta_de_resolucion,
    match_proxies,
)


def test_empareja_por_stem_mas_sufijo_s03():
    originales = [Path("/cam/20260804_PIB0587.MP4")]
    proxies = [Path("/proxies/20260804_PIB0587S03.MP4")]
    result = match_proxies(originales, proxies)
    assert result[Path("/cam/20260804_PIB0587.MP4")] == Path("/proxies/20260804_PIB0587S03.MP4")


def test_original_sin_proxy_correspondiente_queda_none():
    originales = [Path("/cam/DJI_0001.MP4")]
    proxies: list[Path] = []
    result = match_proxies(originales, proxies)
    assert result[Path("/cam/DJI_0001.MP4")] is None


def test_no_confunde_prefijos_parecidos():
    originales = [Path("/cam/C001.MP4"), Path("/cam/C0010.MP4")]
    proxies = [Path("/proxies/C0010S03.MP4")]
    result = match_proxies(originales, proxies)
    assert result[Path("/cam/C001.MP4")] is None
    assert result[Path("/cam/C0010.MP4")] == Path("/proxies/C0010S03.MP4")


# --- buscar_proxies: el paso que faltaba (F9) ---------------------------
#
# match_proxies() recibe dos listas ya armadas y nadie las armaba. Buscar
# los candidatos es su propio problema porque Bruno guarda los proxies en
# una carpeta APARTE de los originales, asi que mirar solo la carpeta
# importada no alcanza.


def _video(carpeta: Path, nombre: str) -> Path:
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / nombre
    ruta.touch()
    return ruta


def test_encuentra_el_proxy_en_una_carpeta_hermana(tmp_path):
    """El caso real de Bruno (`clips/` y `proxy/`) y el de la tarjeta Sony
    (`CLIP/` y `SUB/`): el proxy nunca esta donde estan los originales."""
    _video(tmp_path / "clips", "20260804_PIB0587.MP4")
    proxy = _video(tmp_path / "proxy", "20260804_PIB0587S03.MP4")

    assert buscar_proxies(tmp_path / "clips") == [proxy]


def test_encuentra_el_proxy_suelto_en_la_carpeta_padre(tmp_path):
    _video(tmp_path / "clips", "C0001.MP4")
    proxy = _video(tmp_path, "C0001S03.MP4")

    assert buscar_proxies(tmp_path / "clips") == [proxy]


def test_encuentra_el_proxy_revuelto_con_los_originales(tmp_path):
    """Que Bruno los separe no puede convertirse en una limitacion: si
    algun dia vienen juntos, tienen que emparejarse igual."""
    carpeta = tmp_path / "clips"
    _video(carpeta, "C0001.MP4")
    proxy = _video(carpeta, "C0001S03.MP4")

    assert buscar_proxies(carpeta) == [proxy]


def test_no_baja_mas_alla_del_tope_de_profundidad(tmp_path):
    """Sin tope, importar algo de la raiz de un volumen lo recorre entero."""
    _video(tmp_path / "clips", "C0001.MP4")
    _video(tmp_path / "otra" / "adentro" / "mas", "C0001S03.MP4")

    assert PROFUNDIDAD_DE_BUSQUEDA == 2
    assert buscar_proxies(tmp_path / "clips") == []


def test_sin_ningun_s03_devuelve_lista_vacia(tmp_path):
    _video(tmp_path / "clips", "DJI_0001.MP4")

    assert buscar_proxies(tmp_path / "clips") == []


def test_ignora_archivos_que_no_son_de_video(tmp_path):
    _video(tmp_path / "clips", "C0001.MP4")
    _video(tmp_path, "C0001S03.txt")

    assert buscar_proxies(tmp_path / "clips") == []


def test_una_carpeta_inaccesible_no_revienta(tmp_path):
    """Importar de un volumen ajeno con permisos raros no puede tumbar la
    app: devuelve lo que pudo leer y sigue."""
    carpeta = tmp_path / "clips"
    _video(carpeta, "C0001.MP4")
    prohibida = tmp_path / "prohibida"
    prohibida.mkdir()
    prohibida.chmod(0o000)
    try:
        assert buscar_proxies(carpeta) == []
    finally:
        prohibida.chmod(0o755)


def test_una_carpeta_que_no_existe_devuelve_vacio(tmp_path):
    assert buscar_proxies(tmp_path / "no-existe" / "clips") == []


def test_no_devuelve_el_mismo_proxy_dos_veces(tmp_path):
    """La carpeta importada esta DENTRO del padre que se recorre: sin
    cuidado, el proxy revuelto con los originales sale duplicado."""
    carpeta = tmp_path / "clips"
    _video(carpeta, "C0001.MP4")
    proxy = _video(carpeta, "C0001S03.MP4")

    assert buscar_proxies(carpeta) == [proxy]


# --- etiqueta_de_resolucion --------------------------------------------


def test_la_etiqueta_sale_del_lado_corto():
    """Un proxy vertical de 1080x1920 es 1080p, no 1920p."""
    assert etiqueta_de_resolucion(1920, 1080) == "1080p"
    assert etiqueta_de_resolucion(1080, 1920) == "1080p"


def test_la_etiqueta_del_proxy_real_de_bruno_es_720p():
    """El S03 de la FX30 mide 1280x720 -- el `Proxy 1080p` del mockup era
    un dibujo, no un dato."""
    assert etiqueta_de_resolucion(1280, 720) == "720p"
    assert etiqueta_de_resolucion(720, 1280) == "720p"


def test_sin_tamano_no_hay_etiqueta():
    assert etiqueta_de_resolucion(0, 0) == ""
