from pathlib import Path

from clasificador_video.buscar_prproj import buscar_por_folio


def _tocar(ruta: Path, contenido: bytes = b"x") -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(contenido)


def test_una_sola_coincidencia(tmp_path):
    raiz = tmp_path / "IAV"
    _tocar(raiz / "2026" / "09. Septiembre" / "IAV-2609.10-A.prproj")

    resultado = buscar_por_folio(raiz, "IAV-2609.10-A")

    assert len(resultado) == 1
    assert resultado[0].name == "IAV-2609.10-A.prproj"


def test_varias_versiones_ordenadas_por_fecha_mas_nueva_primero(tmp_path):
    import os
    import time

    raiz = tmp_path / "IAV"
    vieja = raiz / "2026" / "09. Septiembre" / "IAV-2609.10-A.prproj"
    nueva = raiz / "2026" / "09. Septiembre" / "IAV-2609.10-A V2.prproj"
    _tocar(vieja)
    time.sleep(0.01)
    _tocar(nueva)
    os.utime(nueva, None)  # asegura mtime >= al de "vieja" en cualquier FS

    resultado = buscar_por_folio(raiz, "IAV-2609.10-A")

    assert [r.name for r in resultado] == [
        "IAV-2609.10-A V2.prproj", "IAV-2609.10-A.prproj",
    ]


def test_sin_coincidencia_devuelve_lista_vacia(tmp_path):
    raiz = tmp_path / "IAV"
    _tocar(raiz / "2026" / "09. Septiembre" / "otro-folio.prproj")

    assert buscar_por_folio(raiz, "IAV-2609.10-A") == []


def test_no_confunde_folios_que_empiezan_igual(tmp_path):
    """"2609.1" no debe encontrar "2609.10-A": el folio se busca como
    substring exacto, y un folio corto que calza por accidente dentro de
    uno mas largo traeria el proyecto equivocado."""
    raiz = tmp_path / "IAV"
    _tocar(raiz / "2026" / "IAV-2609.10-A.prproj")

    assert buscar_por_folio(raiz, "IAV-2609.1") == []


def test_carpeta_raiz_que_no_existe_no_truena(tmp_path):
    assert buscar_por_folio(tmp_path / "no existe", "cualquiera") == []
