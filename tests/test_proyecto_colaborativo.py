"""Parseo del folio y armado de la ruta del proyecto en iCloud, sin Qt ni
red -- spec 2026-09-23-proyecto-colaborativo-icloud-design.md."""
from pathlib import Path

from clasificador_video import proyecto_colaborativo as colab


def test_partir_folio_negocio_iav():
    partido = colab.partir_folio("IAV-2609.10-A")

    assert partido.negocio == "IAV"
    assert partido.anio == 2026
    assert partido.mes == 9


def test_partir_folio_negocio_pi():
    partido = colab.partir_folio("PI-2701.05-B")

    assert partido.negocio == "PI"
    assert partido.anio == 2027
    assert partido.mes == 1


def test_partir_folio_negocio_desconocido_no_parsea():
    assert colab.partir_folio("XYZ-2609.10-A") is None


def test_partir_folio_mes_invalido_no_parsea():
    assert colab.partir_folio("IAV-2613.10-A") is None


def test_partir_folio_formato_raro_no_parsea():
    assert colab.partir_folio("no es un folio") is None
    assert colab.partir_folio("") is None


def test_ruta_del_proyecto_arma_negocio_anio_mes_folio(tmp_path):
    raiz = tmp_path

    ruta = colab.ruta_del_proyecto(raiz, "IAV-2609.10-A")

    assert ruta == (
        raiz / "01. IAV" / "2026" / "09. Septiembre" / "IAV-2609.10-A"
    )


def test_ruta_del_proyecto_negocio_pi(tmp_path):
    ruta = colab.ruta_del_proyecto(tmp_path, "PI-2701.05-B")

    assert ruta == (
        tmp_path / "02. PI" / "2027" / "01. Enero" / "PI-2701.05-B"
    )


def test_ruta_del_proyecto_folio_invalido_da_none(tmp_path):
    assert colab.ruta_del_proyecto(tmp_path, "no es un folio") is None
