# tests/test_proxy_gen.py
import subprocess
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


class _FfmpegFalso:
    """Un `Popen` de mentira: escribe el archivo de salida y termina.

    `vueltas_colgado` simula un ffmpeg que tarda: `communicate` levanta
    `TimeoutExpired` esas veces antes de devolver, que es cuando la funcion
    consulta si la cancelaron.
    """

    def __init__(self, args, vueltas_colgado=0, returncode=0, stderr="", **kwargs):
        self._destino = Path(args[-1])
        self._faltan = vueltas_colgado
        self.returncode = returncode
        self._stderr = stderr
        self.terminado = False

    def communicate(self, timeout=None):
        if self._faltan > 0:
            self._faltan -= 1
            raise subprocess.TimeoutExpired(cmd="ffmpeg", timeout=timeout)
        if self.returncode == 0:
            self._destino.write_bytes(b"video")
        return "", self._stderr

    def terminate(self):
        self.terminado = True

    def wait(self, timeout=None):
        return self.returncode

    def kill(self):
        self.terminado = True


def test_generar_escribe_a_un_parcial_y_renombra_al_final(tmp_path, monkeypatch):
    """Sin el temporal, cancelar o quedarse sin disco a la mitad deja un mp4
    truncado CON EL NOMBRE BUENO -- y la corrida siguiente lo da por hecho y
    lo engancha. Un proxy a medias es peor que ninguno: se ve, y miente sobre
    donde termina el clip."""
    vistos = []

    def falso_popen(args, **kwargs):
        vistos.append(Path(args[-1]).name)
        return _FfmpegFalso(args)

    monkeypatch.setattr(proxy_gen.subprocess, "Popen", falso_popen)

    destino = proxy_gen.generar(Path("/m/DJI_0001.MP4"), tmp_path / "Proxies",
                                ffmpeg="ffmpeg")

    assert vistos == ["DJI_0001S03.mp4.parcial"]   # ffmpeg escribio al temporal
    assert destino.name == "DJI_0001S03.mp4"       # y quedo con el nombre bueno
    assert destino.exists()


def test_si_ffmpeg_falla_no_queda_basura_ni_se_dice_que_si(tmp_path, monkeypatch):
    monkeypatch.setattr(
        proxy_gen.subprocess, "Popen",
        lambda args, **k: _FfmpegFalso(
            args, returncode=1, stderr="Invalid data found when processing input"),
    )
    carpeta = tmp_path / "Proxies"

    with pytest.raises(RuntimeError, match="Invalid data"):
        proxy_gen.generar(Path("/m/DJI_0001.MP4"), carpeta, ffmpeg="ffmpeg")

    assert list(carpeta.iterdir()) == []


def test_cancelar_corta_ffmpeg_en_vez_de_esperarlo(tmp_path, monkeypatch):
    """Antes esto era una llamada que no se podia interrumpir: al cerrar la
    app durante una tanda, la ventana se quedaba congelada hasta que
    terminara el clip en curso -- y con una toma de dron de tres minutos y
    medio, eso son varios minutos mirando una app muerta."""
    procesos = []

    def falso_popen(args, **kwargs):
        proceso = _FfmpegFalso(args, vueltas_colgado=10)
        procesos.append(proceso)
        return proceso

    monkeypatch.setattr(proxy_gen.subprocess, "Popen", falso_popen)
    carpeta = tmp_path / "Proxies"

    with pytest.raises(proxy_gen.Interrumpido):
        proxy_gen.generar(Path("/m/DJI_0001.MP4"), carpeta, ffmpeg="ffmpeg",
                          cancelado=lambda: True, latido=0.001)

    assert procesos[0].terminado                 # se le corto, no se espero
    assert list(carpeta.iterdir()) == []         # y no quedo el .parcial
