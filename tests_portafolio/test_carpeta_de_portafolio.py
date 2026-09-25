"""La carpeta de portafolio: dónde le tocaría vivir a cada clip Elegido,
en una subcarpeta por proyecto de origen -- spec
2026-09-24-modo-portafolio-design.md.

Esta pieza SOLO calcula rutas. Crear el alias real (Finder, macOS) es
la Fase 4.5 -- ver crear_alias_de_finder.py.
"""
from pathlib import Path

from clasificador_video_portafolio import carpeta_de_portafolio as cp


def test_ruta_del_alias_usa_subcarpeta_del_proyecto(tmp_path):
    carpeta_raiz = tmp_path / "Mi Portafolio"
    original = tmp_path / "material" / "clip_014.mov"

    ruta = cp.ruta_del_alias(carpeta_raiz, proyecto="Casa Reforma", clip=original)

    assert ruta == carpeta_raiz / "Casa Reforma" / "clip_014.mov"


def test_ruta_de_proxy_vive_junto_al_alias(tmp_path):
    carpeta_raiz = tmp_path / "Mi Portafolio"
    original = tmp_path / "material" / "clip_014.mov"

    ruta = cp.ruta_de_proxy(carpeta_raiz, proyecto="Casa Reforma", clip=original)

    assert ruta.parent == carpeta_raiz / "Casa Reforma"


def test_ruta_de_proxy_lleva_el_sufijo_para_no_chocar_con_el_alias(tmp_path):
    carpeta_raiz = tmp_path / "Mi Portafolio"
    original = tmp_path / "material" / "clip_014.mov"

    ruta = cp.ruta_de_proxy(carpeta_raiz, proyecto="Casa Reforma", clip=original)

    assert ruta.name == "clip_014_proxy.mp4"
    assert ruta != cp.ruta_del_alias(carpeta_raiz, proyecto="Casa Reforma", clip=original)


def test_asegurar_subcarpeta_de_proyecto_la_crea_si_falta(tmp_path):
    carpeta_raiz = tmp_path / "Mi Portafolio"

    destino = cp.asegurar_subcarpeta_de_proyecto(carpeta_raiz, proyecto="Casa Reforma")

    assert destino.is_dir()
    assert destino == carpeta_raiz / "Casa Reforma"


def test_generar_proxy_faltante_llama_a_proxy_gen(tmp_path, monkeypatch):
    llamadas = []
    monkeypatch.setattr(
        "clasificador_video_portafolio.carpeta_de_portafolio.proxy_gen.generar",
        lambda origen, destino: llamadas.append((origen, destino)),
    )
    original = tmp_path / "clip_014.mov"
    original.write_text("x")
    carpeta_raiz = tmp_path / "Mi Portafolio"

    cp.asegurar_proxy(carpeta_raiz, proyecto="Casa Reforma", clip=original)

    assert len(llamadas) == 1
    # El nuevo proxy cae dentro de la subcarpeta del proyecto de origen.
    assert llamadas[0][1] == carpeta_raiz / "Casa Reforma"


def test_no_regenera_si_ya_existe_proxy_en_la_carpeta_de_portafolio(tmp_path, monkeypatch):
    llamadas = []
    monkeypatch.setattr(
        "clasificador_video_portafolio.carpeta_de_portafolio.proxy_gen.generar",
        lambda origen, destino: llamadas.append((origen, destino)),
    )
    original = tmp_path / "clip_014.mov"
    original.write_text("x")
    carpeta_raiz = tmp_path / "Mi Portafolio"
    ruta_proxy = cp.ruta_de_proxy(carpeta_raiz, proyecto="Casa Reforma", clip=original)
    ruta_proxy.parent.mkdir(parents=True)
    ruta_proxy.write_text("ya existe")

    devuelta = cp.asegurar_proxy(carpeta_raiz, proyecto="Casa Reforma", clip=original)

    assert llamadas == []
    assert devuelta == ruta_proxy


def test_reusa_un_proxy_encontrado_junto_al_material(tmp_path, monkeypatch):
    llamadas = []
    monkeypatch.setattr(
        "clasificador_video_portafolio.carpeta_de_portafolio.proxy_gen.generar",
        lambda origen, destino: llamadas.append((origen, destino)),
    )
    material = tmp_path / "01. VIDEOS SONY"
    material.mkdir()
    original = material / "clip_014.mov"
    original.write_text("x")
    (tmp_path / "Proxies").mkdir()
    ya_hecho = tmp_path / "Proxies" / "clip_014_proxy.mp4"
    ya_hecho.write_text("proxy de otra entrega")

    devuelta = cp.asegurar_proxy(
        tmp_path / "Mi Portafolio", proyecto="Casa Reforma", clip=original
    )

    assert llamadas == []
    assert devuelta == ya_hecho

