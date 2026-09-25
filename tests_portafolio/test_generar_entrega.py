"""Generar la entrega: un .prproj con bins por proyecto de origen.

Reusa `prproj_generador.generar_prproj` -- la misma pieza que ya usa el
Clipify normal para su propia entrega -- aplicada a clips que vienen del
portafolio en vez de un .cvproj de rodaje. Spec:
docs/superpowers/specs/2026-09-24-modo-portafolio-design.md.
"""
from datetime import date

from clasificador_video_portafolio import generar_entrega as ge
from clasificador_video_portafolio import portafolio as pf


def test_nombre_de_archivo_lleva_la_fecha():
    nombre = ge.nombre_de_archivo("Mi Portafolio", fecha=date(2026, 9, 24))

    assert nombre == "Mi Portafolio — entrega 2026-09-24.prproj"


def test_nombre_de_archivo_sin_fecha_usa_hoy():
    nombre = ge.nombre_de_archivo("Mi Portafolio")

    assert date.today().isoformat() in nombre


def test_bins_agrupan_por_proyecto_con_su_categoria(tmp_path):
    clips = [
        pf.ClipDelPortafolio(ruta_origen=tmp_path / "a.mov", proyecto="Casa Reforma"),
        pf.ClipDelPortafolio(ruta_origen=tmp_path / "b.mov", proyecto="Casa Reforma"),
        pf.ClipDelPortafolio(ruta_origen=tmp_path / "c.mov", proyecto="Torre Insurgentes"),
    ]
    categorias = {"Casa Reforma": "Casa", "Torre Insurgentes": "Depto"}

    bins = ge.agrupar_en_bins(clips, categorias)

    assert bins["Casa Reforma — Casa"] == clips[:2]
    assert bins["Torre Insurgentes — Depto"] == clips[2:]


def test_bins_sin_categoria_usan_solo_el_nombre_del_proyecto(tmp_path):
    clips = [pf.ClipDelPortafolio(ruta_origen=tmp_path / "a.mov", proyecto="Rancho")]

    bins = ge.agrupar_en_bins(clips, {})

    assert list(bins) == ["Rancho"]


def test_generar_arma_el_manifest_con_rutas_de_portafolio(tmp_path, monkeypatch):
    clips = [
        pf.ClipDelPortafolio(tmp_path / "material" / "a.mov", "Casa Reforma"),
        pf.ClipDelPortafolio(tmp_path / "material" / "DJI_002.mov", "Torre Insurgentes"),
    ]
    categorias = {"Casa Reforma": "Casa", "Torre Insurgentes": "Depto"}
    capturado = {}
    monkeypatch.setattr(
        ge.prproj_generador, "generar_prproj",
        lambda manifest, destino, carpeta_luts, **resto: capturado.update(
            manifest=manifest, destino=destino, carpeta_luts=carpeta_luts),
    )
    monkeypatch.setattr(
        ge.cp, "asegurar_proxy",
        lambda carpeta_raiz, proyecto, clip: tmp_path / "proxy" / f"{clip.stem}_proxy.mp4",
    )
    carpeta_raiz = tmp_path / "Mi Portafolio"

    destino = ge.generar(
        clips, categorias, carpeta_raiz, fecha=date(2026, 9, 24)
    )

    assert destino == carpeta_raiz / "Mi Portafolio — entrega 2026-09-24.prproj"
    assert capturado["destino"] == destino
    assert capturado["carpeta_luts"] == carpeta_raiz / "LUTs"
    manifest = capturado["manifest"]
    assert [c.categoria_path for c in manifest.clips] == [
        ["Casa Reforma — Casa"], ["Torre Insurgentes — Depto"],
    ]
    assert manifest.clips[0].ruta == ge.cp.ruta_del_alias(
        carpeta_raiz, "Casa Reforma", tmp_path / "material" / "a.mov")
    assert manifest.clips[1].camara == "dji"


def test_generar_de_verdad_hace_un_prproj_con_el_bin_del_proyecto(tmp_path):
    """Integración real: el .prproj sale con el bin y la ruta del alias."""
    from clasificador_video import prproj_xml

    original = tmp_path / "material" / "a.mov"
    original.parent.mkdir(parents=True)
    original.write_bytes(b"")
    clips = [pf.ClipDelPortafolio(original, "Casa Reforma")]
    carpeta_raiz = tmp_path / "Mi Portafolio"

    def probe_falso(_ruta):
        return {"width": 1920, "height": 1080, "fps": 29.97,
                "duration_seconds": 4.0, "rotation": 0}

    destino = ge.generar(
        clips, {"Casa Reforma": "Casa"}, carpeta_raiz,
        fecha=date(2026, 9, 24), probe=probe_falso,
        generador_proxy=lambda carpeta, proyecto, clip: tmp_path / "no-existe_proxy.mp4",
    )

    assert destino.is_file()
    raiz = prproj_xml.leer_prproj(destino)
    assert "01. Casa Reforma — Casa" in [
        nodo.text for nodo in raiz.iter("Name")]
    alias = ge.cp.ruta_del_alias(carpeta_raiz, "Casa Reforma", original)
    assert str(alias) in [nodo.text for nodo in raiz.iter("FilePath")]
