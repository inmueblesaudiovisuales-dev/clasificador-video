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


def test_en_la_app_empaquetada_el_patron_sigue_ahi(tmp_path, monkeypatch):
    """El bug del 2026-09-15: `docs/` no viaja en el `.dmg`.

    La ruta del repo --tres carpetas arriba de este archivo-- no existe
    dentro del paquete de PyInstaller, así que `leer()` devolvía "" y la
    guía salía con el orden de manual en vez del de Bruno. Y en silencio:
    no fallaba, solo salía genérica.
    """
    import sys

    empaquetada = tmp_path / "MEIPASS"
    (empaquetada / "docs" / "patron-de-recorrido").mkdir(parents=True)
    (empaquetada / "docs" / "patron-de-recorrido" / "MI-PATRON.md").write_text(
        "Abres por fuera.", encoding="utf-8"
    )
    monkeypatch.setattr(sys, "_MEIPASS", str(empaquetada), raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)

    assert patron.leer() == "Abres por fuera."


def test_el_patron_habla_de_la_aerea_de_en_medio():
    # Lo que Bruno dijo el 2026-09-15 y el documento no tenía.
    texto = patron.leer()
    assert "a media casa" in texto


def test_el_patron_cierra_con_dos_aereas():
    texto = patron.leer()
    assert "de lejos" in texto


def test_el_patron_sigue_sin_cuentas():
    # La regla del §5.1 del spec del patrón, comprobada y no confiada.
    import re

    texto = patron.leer()
    assert not re.search(
        r"[0-9]+ ?%|\([0-9]+ (videos|casos)\)|la mayoría|de cada", texto
    )


def test_el_patron_va_en_la_receta_de_empaquetado():
    """Y que la receta de verdad lo incluya. Sin esto, el arreglo de arriba
    busca un archivo que nadie copió."""
    from pathlib import Path

    receta = Path(__file__).resolve().parents[1] / "empaque" / "clipify.spec"
    texto = receta.read_text(encoding="utf-8")
    assert "patron-de-recorrido" in texto
    assert "datas=[]" not in texto
