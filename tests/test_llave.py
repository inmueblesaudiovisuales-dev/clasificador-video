from pathlib import Path

from clasificador_video import llave as mod


def test_guardar_y_leer(tmp_path: Path):
    destino = tmp_path / "llave.json"
    mod.guardar("sk-123456789abcd", destino)
    assert mod.leer(destino) == "sk-123456789abcd"


def test_sin_llave_devuelve_vacio(tmp_path: Path):
    # La primera vez no hay llave, y eso no es un error.
    assert mod.leer(tmp_path / "no-existe.json") == ""


def test_un_archivo_roto_devuelve_vacio(tmp_path: Path):
    destino = tmp_path / "llave.json"
    destino.write_text("{esto no es json", encoding="utf-8")
    assert mod.leer(destino) == ""


def test_borrar(tmp_path: Path):
    destino = tmp_path / "llave.json"
    mod.guardar("sk-123456789abcd", destino)
    mod.borrar(destino)
    assert mod.leer(destino) == ""


def test_borrar_lo_que_no_esta_no_revienta(tmp_path: Path):
    mod.borrar(tmp_path / "no-existe.json")


def test_tapada_ensena_los_ultimos_cuatro():
    assert mod.tapada("sk-123456789abcd") == "••••••••abcd"


def test_una_llave_corta_se_tapa_entera():
    # Ensenar los ultimos cuatro de una llave corta es ensenar media llave,
    # y el punto de taparla es que alguien pueda ver la pantalla de Bruno
    # sin llevarse nada.
    assert mod.tapada("sk-123") == "••••••••"


def test_sin_llave_no_hay_nada_que_tapar():
    assert mod.tapada("") == ""
