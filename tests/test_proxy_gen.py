# tests/test_proxy_gen.py
from pathlib import Path

import pytest

from clasificador_video import proxy_gen


def test_la_carpeta_va_al_lado_del_material_no_adentro():
    """Adentro ensuciaria la copia de la tarjeta, que es lo que uno quiere
    poder volver a copiar tal cual. Bruno lo eligio asi: «al lado»."""
    assert proxy_gen.carpeta_de_proxies(Path("/media/DRON")) == Path("/media/Proxies")


def test_el_proxy_lleva_el_sufijo_de_proxy_y_sale_en_mp4():
    """El sufijo `S03` no es cosmetica: `ingest.es_archivo_de_proxy` descarta
    por el, asi que arrastrar la carpeta de proxies como si fuera material no
    duplica nada."""
    destino = proxy_gen.ruta_de_proxy(Path("/m/DRON/DJI_0001.MP4"), Path("/m/Proxies"))

    assert destino == Path("/m/Proxies/DJI_0001S03.mp4")


def test_el_comando_toma_la_primera_pista_de_video():
    """Los MP4 del dron traen una miniatura JPEG incrustada como SEGUNDA
    pista de video. Sin `-map 0:v:0` ffmpeg transcodifica ESA --la elige por
    ser la de mejor "calidad"-- y sale un proxy de 406 px de ancho. Costo una
    medicion entera descubrirlo."""
    args = proxy_gen.comando(Path("a.MP4"), Path("b.mp4"), ffmpeg="ffmpeg")

    assert "-map" in args
    assert args[args.index("-map") + 1] == "0:v:0"


def test_el_comando_escala_por_el_lado_corto():
    """`scale=-2:720` a secas deja un clip VERTICAL en 720 de ancho, o sea
    720x1280 donde deberia dar 405x720 -- un proxy mas pesado que el
    original en el peor caso."""
    args = proxy_gen.comando(Path("a.MP4"), Path("b.mp4"), ffmpeg="ffmpeg")
    filtro = args[args.index("-vf") + 1]

    assert "gt(iw,ih)" in filtro   # decide mirando cual lado es el corto
    assert "720" in filtro


def test_el_comando_no_falla_si_el_clip_no_trae_audio():
    """El `?` de `0:a?`. Sin el, un clip mudo --pasa con el dron-- aborta
    ffmpeg antes de empezar."""
    args = proxy_gen.comando(Path("a.MP4"), Path("b.mp4"), ffmpeg="ffmpeg")

    assert "0:a?" in args


def test_faltantes_deja_fuera_los_que_ya_tienen_proxy(tmp_path):
    """Volver a darle a «Crear proxies» no rehace lo hecho. Es el caso normal
    despues de cancelar a la mitad: con 23 tomas, rehacerlas son minutos
    tirados."""
    proxies = tmp_path / "Proxies"
    proxies.mkdir()
    (proxies / "DJI_0001S03.mp4").touch()
    originales = [Path("/m/DJI_0001.MP4"), Path("/m/DJI_0002.MP4")]

    assert proxy_gen.faltantes(originales, proxies) == [Path("/m/DJI_0002.MP4")]


def test_generar_escribe_a_un_parcial_y_renombra_al_final(tmp_path, monkeypatch):
    """Sin el temporal, cancelar o quedarse sin disco a la mitad deja un mp4
    truncado CON EL NOMBRE BUENO -- y la corrida siguiente lo da por hecho y
    lo engancha. Un proxy a medias es peor que ninguno: se ve, y miente sobre
    donde termina el clip."""
    vistos = []

    class Resultado:
        returncode = 0
        stderr = ""

    def falso_run(args, **kwargs):
        destino = Path(args[-1])
        vistos.append(destino.name)
        destino.write_bytes(b"video")
        return Resultado()

    monkeypatch.setattr(proxy_gen.subprocess, "run", falso_run)

    destino = proxy_gen.generar(Path("/m/DJI_0001.MP4"), tmp_path / "Proxies",
                                ffmpeg="ffmpeg")

    assert vistos == ["DJI_0001S03.mp4.parcial"]   # ffmpeg escribio al temporal
    assert destino.name == "DJI_0001S03.mp4"       # y quedo con el nombre bueno
    assert destino.exists()


def test_si_ffmpeg_falla_no_queda_basura_ni_se_dice_que_si(tmp_path, monkeypatch):
    class Resultado:
        returncode = 1
        stderr = "Invalid data found when processing input"

    def falso_run(args, **kwargs):
        Path(args[-1]).write_bytes(b"a medias")
        return Resultado()

    monkeypatch.setattr(proxy_gen.subprocess, "run", falso_run)
    carpeta = tmp_path / "Proxies"

    with pytest.raises(RuntimeError, match="Invalid data"):
        proxy_gen.generar(Path("/m/DJI_0001.MP4"), carpeta, ffmpeg="ffmpeg")

    assert list(carpeta.iterdir()) == []
