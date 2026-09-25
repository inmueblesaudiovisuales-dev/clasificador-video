"""El alias de Finder de verdad -- spec
2026-09-24-modo-portafolio-design.md. Solo corre en macOS."""
import sys

import pytest

from clasificador_video_portafolio import crear_alias_de_finder as caf

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin", reason="el alias de Finder solo existe en macOS"
)


def test_crear_alias_hace_la_subcarpeta_si_falta(tmp_path):
    original = tmp_path / "clip_014.mov"
    original.write_text("contenido")
    destino = tmp_path / "Mi Portafolio" / "Casa Reforma" / "clip_014.mov"

    caf.crear(original, destino)

    assert destino.parent.is_dir()


def test_crear_alias_resuelve_al_original(tmp_path):
    original = tmp_path / "clip_014.mov"
    original.write_text("contenido")
    destino = tmp_path / "Mi Portafolio" / "Casa Reforma" / "clip_014.mov"

    caf.crear(original, destino)

    assert caf.resolver(destino) == original.resolve()


def test_crear_alias_sigue_resolviendo_si_el_original_se_renombra(tmp_path):
    original = tmp_path / "clip_014.mov"
    original.write_text("contenido")
    destino = tmp_path / "Mi Portafolio" / "Casa Reforma" / "clip_014.mov"

    caf.crear(original, destino)
    renombrado = tmp_path / "clip_014_final.mov"
    original.rename(renombrado)

    assert caf.resolver(destino) == renombrado.resolve()


def test_crear_alias_no_pisa_uno_ya_existente(tmp_path):
    original = tmp_path / "clip_014.mov"
    original.write_text("contenido")
    destino = tmp_path / "Mi Portafolio" / "Casa Reforma" / "clip_014.mov"
    caf.crear(original, destino)
    creado_en = destino.stat().st_mtime_ns

    caf.crear(original, destino)

    assert destino.stat().st_mtime_ns == creado_en
