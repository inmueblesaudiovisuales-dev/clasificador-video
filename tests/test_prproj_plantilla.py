"""Localizar arquetipos dentro de la plantilla real."""
import pytest

from clasificador_video import prproj_plantilla, prproj_xml, recursos


@pytest.fixture
def raiz():
    return prproj_xml.leer_prproj(recursos.template_color_luts())


def test_archetipos_de_clip_encuentra_sony_y_dji(raiz):
    assert set(prproj_plantilla.archetipos_de_clip(raiz)) == {"sony", "dji", "otra"}


def test_archetipo_sony_tiene_el_lut_correcto(raiz):
    assert prproj_plantilla.archetipos_de_clip(raiz)["sony"].ruta_lut.endswith("SONY-SLOG3.cube")


def test_archetipo_dji_tiene_el_lut_correcto(raiz):
    assert prproj_plantilla.archetipos_de_clip(raiz)["dji"].ruta_lut.endswith("DJI-DLOGM.cube")


def test_archetipo_otra_no_tiene_lut(raiz):
    assert prproj_plantilla.archetipos_de_clip(raiz)["otra"].ruta_lut is None


def test_archetipo_de_bin_existe(raiz):
    assert prproj_plantilla.archetipo_de_bin(raiz) is not None


def test_archetipo_de_secuencia_es_un_clip_project_item_completo(raiz):
    arquetipo = prproj_plantilla.archetipo_de_secuencia(raiz)
    item = next(i for i in raiz.findall("ClipProjectItem")
                if i.get("ObjectUID") == arquetipo.clip_project_item_uid)
    master_ref = item.find("MasterClip")
    master = next(m for m in raiz.findall("MasterClip")
                  if m.get("ObjectUID") == master_ref.get("ObjectURef"))
    fuentes = []
    for clip_ref in master.findall("Clips/Clip"):
        clip = next(c for c in raiz if c.get("ObjectID") == clip_ref.get("ObjectRef"))
        fuente_ref = clip.find("Clip/Source")
        fuente = next(c for c in raiz if c.get("ObjectID") == fuente_ref.get("ObjectRef"))
        fuentes.append(fuente)
    assert {f.tag for f in fuentes} == {"VideoSequenceSource", "AudioSequenceSource"}
    assert arquetipo.sequence_uid in {
        f.find("SequenceSource/Sequence").get("ObjectURef") for f in fuentes}


def test_archetipo_de_secuencia_esta_vacio(raiz):
    arquetipo = prproj_plantilla.archetipo_de_secuencia(raiz)
    secuencia = next(s for s in raiz.findall("Sequence")
                     if s.get("ObjectUID") == arquetipo.sequence_uid)
    for grupo_ref in secuencia.findall(".//TrackGroup/Second"):
        grupo = next(c for c in raiz if c.get("ObjectID") == grupo_ref.get("ObjectRef"))
        for track_ref in grupo.findall(".//Track"):
            track = next(c for c in raiz if c.get("ObjectUID") == track_ref.get("ObjectURef"))
            assert track.findall(".//TrackItem") == []


def test_archetipo_de_secuencia_no_es_el_clip_otra(raiz):
    arquetipo = prproj_plantilla.archetipo_de_secuencia(raiz)
    por_camara = prproj_plantilla.archetipos_de_clip(raiz)
    assert por_camara["otra"].master_clip_uid != arquetipo.clip_project_item_uid


def test_plantilla_incompleta_avisa_en_vez_de_adivinar():
    raiz = prproj_xml.leer_prproj(recursos.template_color_luts())
    for elemento in list(raiz):
        if elemento.tag in ("VideoClip", "AudioClip", "ClipProjectItem"):
            raiz.remove(elemento)
    with pytest.raises(prproj_plantilla.PlantillaIncompleta):
        prproj_plantilla.archetipos_de_clip(raiz)


def test_arquetipo_de_proxy_exige_medio_proxy_y_enlaces_de_audio():
    raiz = prproj_xml.leer_prproj(recursos.template_proxy_adjunto())

    arquetipo = prproj_plantilla.arquetipo_de_proxy(raiz)

    assert raiz.find(
        f'.//Media[@ObjectUID="{arquetipo.proxy_media_uid}"]/IsProxy'
    ).text == "true"
    assert arquetipo.video_media_source_id
    assert arquetipo.audio_media_source_id
    assert len(arquetipo.proxy_audio_stream_ids) > 0
