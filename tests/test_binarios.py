# tests/test_binarios.py
import sys

import pytest

from clasificador_video.binarios import BinarioFaltante, esta_disponible, ruta_de


def test_fuera_del_paquete_usa_el_del_sistema():
    assert ruta_de("ffprobe").name == "ffprobe"
    assert ruta_de("ffprobe").exists()


def test_dentro_del_paquete_usa_el_que_viaja_adentro(tmp_path, monkeypatch):
    """En la computadora de un compañero no hay Homebrew: los programas
    van ADENTRO del paquete, no en el PATH.

    Comprobado con el paquete real y el PATH limpio: la app abria y no
    importaba un solo clip, porque `ffprobe` se buscaba por nombre.
    """
    adentro = tmp_path / "ffprobe"
    adentro.touch()
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    assert ruta_de("ffprobe") == adentro


def test_si_no_esta_adentro_cae_al_del_sistema(tmp_path, monkeypatch):
    """Un paquete al que le falto copiar algo sigue funcionando en una
    maquina que si lo tiene, en vez de morir por una diferencia de
    empaquetado."""
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    assert ruta_de("ffprobe").exists()


def test_si_no_esta_en_ningun_lado_lo_dice(monkeypatch):
    monkeypatch.setattr("clasificador_video.binarios.shutil.which", lambda _: None)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)

    with pytest.raises(BinarioFaltante) as e:
        ruta_de("ffprobe")
    assert "ffprobe" in str(e.value)


def test_esta_disponible_no_levanta(monkeypatch):
    assert esta_disponible("ffprobe") is True
    monkeypatch.setattr("clasificador_video.binarios.shutil.which", lambda _: None)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    assert esta_disponible("ffprobe") is False
