"""Parseo del folio y armado de la ruta del proyecto en iCloud, sin Qt ni
red -- spec 2026-09-23-proyecto-colaborativo-icloud-design.md."""
from pathlib import Path

import pytest

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


def test_partir_folio_fecha_o_letra_invalidas_no_parsea():
    assert colab.partir_folio("IAV-2602.31-A") is None
    assert colab.partir_folio("IAV-2609.00-A") is None
    assert colab.partir_folio("IAV-2609.10-foo") is None


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


def _con_templates(tmp_path):
    templates = tmp_path / "03. Templates"
    templates.mkdir()
    (templates / colab.TEMPLATE_PREMIERE_NOMBRE).write_text("premiere vacio")
    (templates / colab.TEMPLATE_AE_NOMBRE).write_text("ae vacio")
    return templates


def test_crear_carpeta_de_proyecto_crea_las_8_subcarpetas(tmp_path):
    padre = tmp_path / "09. Septiembre"
    padre.mkdir()
    carpeta_proyecto = padre / "IAV-2609.10-A"
    templates = _con_templates(tmp_path)

    colab.crear_carpeta_de_proyecto(carpeta_proyecto, templates, "IAV-2609.10-A")

    for nombre in colab.SUBCARPETAS:
        assert (carpeta_proyecto / nombre).is_dir()


def test_crear_carpeta_de_proyecto_copia_y_renombra_los_templates(tmp_path):
    padre = tmp_path / "09. Septiembre"
    padre.mkdir()
    carpeta_proyecto = padre / "IAV-2609.10-A"
    templates = _con_templates(tmp_path)

    resultado = colab.crear_carpeta_de_proyecto(
        carpeta_proyecto, templates, "IAV-2609.10-A")

    ruta_prproj = carpeta_proyecto / "01. Proyecto premiere" / "IAV-2609.10-A.prproj"
    ruta_aep = carpeta_proyecto / "02. Proyecto AE" / "IAV-2609.10-A.aep"
    assert ruta_prproj.read_text() == "premiere vacio"
    assert ruta_aep.read_text() == "ae vacio"
    assert resultado.ruta_prproj == ruta_prproj
    assert resultado.ruta_aep == ruta_aep
    assert resultado.ruta_cvproj == (
        carpeta_proyecto / "08. Clipify" / "IAV-2609.10-A.cvproj"
    )


def test_crear_carpeta_de_proyecto_ya_existe_no_toca_nada(tmp_path):
    padre = tmp_path / "09. Septiembre"
    padre.mkdir()
    carpeta_proyecto = padre / "IAV-2609.10-A"
    carpeta_proyecto.mkdir()
    (carpeta_proyecto / "Musica").mkdir()  # algo que Bruno ya puso a mano
    templates = _con_templates(tmp_path)

    with pytest.raises(FileExistsError):
        colab.crear_carpeta_de_proyecto(carpeta_proyecto, templates, "IAV-2609.10-A")

    # lo que ya había sigue exactamente igual
    assert [p.name for p in carpeta_proyecto.iterdir()] == ["Musica"]


def test_crear_carpeta_de_proyecto_sin_carpeta_de_mes_no_la_inventa(tmp_path):
    """La carpeta de negocio/año/mes la arma Bruno a mano de antemano --si
    falta, no se crea sola."""
    carpeta_proyecto = tmp_path / "09. Septiembre" / "IAV-2609.10-A"
    templates = _con_templates(tmp_path)

    with pytest.raises(FileNotFoundError):
        colab.crear_carpeta_de_proyecto(carpeta_proyecto, templates, "IAV-2609.10-A")

    assert not carpeta_proyecto.exists()


def test_crear_carpeta_de_proyecto_sin_template_premiere_no_crea_nada(tmp_path):
    padre = tmp_path / "09. Septiembre"
    padre.mkdir()
    carpeta_proyecto = padre / "IAV-2609.10-A"
    templates = tmp_path / "03. Templates"
    templates.mkdir()
    (templates / colab.TEMPLATE_AE_NOMBRE).write_text("ae vacio")

    with pytest.raises(FileNotFoundError):
        colab.crear_carpeta_de_proyecto(carpeta_proyecto, templates, "IAV-2609.10-A")

    assert not carpeta_proyecto.exists()


def test_crear_carpeta_de_proyecto_sin_template_ae_no_crea_nada(tmp_path):
    padre = tmp_path / "09. Septiembre"
    padre.mkdir()
    carpeta_proyecto = padre / "IAV-2609.10-A"
    templates = tmp_path / "03. Templates"
    templates.mkdir()
    (templates / colab.TEMPLATE_PREMIERE_NOMBRE).write_text("premiere vacio")

    with pytest.raises(FileNotFoundError):
        colab.crear_carpeta_de_proyecto(carpeta_proyecto, templates, "IAV-2609.10-A")

    assert not carpeta_proyecto.exists()


def test_crear_carpeta_de_proyecto_si_falla_la_copia_no_deja_nada(tmp_path, monkeypatch):
    padre = tmp_path / "09. Septiembre"
    padre.mkdir()
    carpeta_proyecto = padre / "IAV-2609.10-A"
    templates = _con_templates(tmp_path)

    def sin_permitir_copiar(*args, **kwargs):
        raise PermissionError("disco sin permiso")

    monkeypatch.setattr(colab.shutil, "copyfile", sin_permitir_copiar)

    with pytest.raises(PermissionError):
        colab.crear_carpeta_de_proyecto(carpeta_proyecto, templates, "IAV-2609.10-A")

    assert not carpeta_proyecto.exists()
