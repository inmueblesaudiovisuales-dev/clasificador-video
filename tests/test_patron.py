from pathlib import Path

from clasificador_video import patron


def test_lee_el_documento(tmp_path: Path):
    doc = tmp_path / "MI-PATRON.md"
    doc.write_text("# Mi patrón\n\nAbres por fuera.\n", encoding="utf-8")
    assert "Abres por fuera." in patron.leer(doc)


def test_sin_documento_devuelve_vacio(tmp_path: Path):
    # Que no exista NO es un error: es un Clipify recién instalado, y la
    # guía tiene que salir igual, nada mas sin el patron adentro.
    assert patron.leer(tmp_path / "no-existe.md") == ""


def test_el_documento_de_verdad_esta_en_su_lugar():
    assert patron.leer().strip() != ""
