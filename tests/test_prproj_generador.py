import pytest

from clasificador_video import prproj_generador, prproj_plantilla, prproj_xml, recursos

TICKS_POR_SEGUNDO = prproj_generador.TICKS_POR_SEGUNDO


@pytest.fixture
def raiz(): return prproj_xml.leer_prproj(recursos.template_color_luts())


def _probe_falso(fps=59.94, duration_seconds=6.006, rotation=0):
    return {"fps": fps, "duration_seconds": duration_seconds, "rotation": rotation, "width": 1080, "height": 1920}


def test_clonar_clip_pone_la_ruta_del_archivo_real(raiz, tmp_path):
    a=prproj_plantilla.archetipos_de_clip(raiz); archivo=tmp_path/'MiClip.MP4'; archivo.write_bytes(b'')
    clon=prproj_generador.clonar_clip(raiz,a['sony'],prproj_xml.AsignadorDeIds(raiz),ruta_archivo=archivo,nombre_en_premiere='✓ Cocina 01 [SONY]',label_name='BE.Prefs.LabelColors.10',label_color=123456,datos_probe=_probe_falso())
    media=raiz.find(f'.//Media[@ObjectUID="{clon.media_uid}"]')
    assert media.find('FilePath').text == str(archivo)
    assert media.find('ActualMediaFilePath').text == str(archivo)
    assert media.find('Title').text == 'MiClip.MP4'


def test_clonar_clip_pone_el_nombre_en_el_project_item(raiz,tmp_path):
    a=prproj_plantilla.archetipos_de_clip(raiz); clon=prproj_generador.clonar_clip(raiz,a['dji'],prproj_xml.AsignadorDeIds(raiz),ruta_archivo=tmp_path/'d.mp4',nombre_en_premiere='★ Jardin 02 [DRONE]',label_name='BE.Prefs.LabelColors.7',label_color=999,datos_probe=_probe_falso())
    assert raiz.find(f'.//ClipProjectItem[@ObjectUID="{clon.clip_project_item_uid}"]').find('.//Name').text == '★ Jardin 02 [DRONE]'


def test_clonar_clip_recalcula_frame_rate_y_duracion_en_ticks(raiz,tmp_path):
    a=prproj_plantilla.archetipos_de_clip(raiz); clon=prproj_generador.clonar_clip(raiz,a['sony'],prproj_xml.AsignadorDeIds(raiz),ruta_archivo=tmp_path/'d.mp4',nombre_en_premiere='x',label_name='x',label_color=1,datos_probe=_probe_falso(25,10))
    stream=next(s for s in raiz.findall('.//VideoStream') if s.find('FrameRate') is not None and s.find('FrameRate').text == str(round(TICKS_POR_SEGUNDO/25)))
    assert int(stream.find('FrameRate').text)==round(TICKS_POR_SEGUNDO/25)
    assert int(stream.find('Duration').text)==round(TICKS_POR_SEGUNDO*10)


def test_clonar_clip_sony_y_dji_comparten_el_mismo_lut_sin_clonarlo(raiz,tmp_path):
    a=prproj_plantilla.archetipos_de_clip(raiz); ids=prproj_xml.AsignadorDeIds(raiz)
    c1=prproj_generador.clonar_clip(raiz,a['sony'],ids,ruta_archivo=tmp_path/'a.mp4',nombre_en_premiere='a',label_name='x',label_color=1,datos_probe=_probe_falso()); c2=prproj_generador.clonar_clip(raiz,a['sony'],ids,ruta_archivo=tmp_path/'b.mp4',nombre_en_premiere='b',label_name='x',label_color=1,datos_probe=_probe_falso())
    refs=[raiz.find(f'.//MasterClip[@ObjectUID="{c.master_clip_uid}"]').find('VideoComponentChain').get('ObjectRef') for c in (c1,c2)]
    assert refs == [a['sony'].video_component_chain_id]*2


def test_clonar_clip_otra_no_tiene_video_component_chain(raiz,tmp_path):
    a=prproj_plantilla.archetipos_de_clip(raiz); c=prproj_generador.clonar_clip(raiz,a['otra'],prproj_xml.AsignadorDeIds(raiz),ruta_archivo=tmp_path/'c.mp4',nombre_en_premiere='c',label_name='x',label_color=1,datos_probe=_probe_falso())
    assert raiz.find(f'.//MasterClip[@ObjectUID="{c.master_clip_uid}"]').find('VideoComponentChain') is None


def test_clonar_secuencia_con_medidas_le_pone_el_nombre(raiz):
    archetipos = prproj_plantilla.archetipos_de_secuencia(raiz)
    clon = prproj_generador.clonar_secuencia_con_medidas(
        raiz, archetipos["4k_9x16"], prproj_xml.AsignadorDeIds(raiz),
        nombre="IAV-2609.10-A 4K 9:16")
    assert clon.find(".//Name").text == "IAV-2609.10-A 4K 9:16"


def test_clonar_secuencia_con_medidas_voltea_para_16x9(raiz):
    archetipos = prproj_plantilla.archetipos_de_secuencia(raiz)
    clon = prproj_generador.clonar_secuencia_con_medidas(
        raiz, archetipos["4k_9x16"], prproj_xml.AsignadorDeIds(raiz),
        nombre="x 4K 16:9", ancho=3840, alto=2160)
    grupo = prproj_plantilla._video_track_group_de_secuencia(raiz, clon)
    assert grupo.find("FrameRect").text == "0,0,3840,2160"


def test_clonar_secuencia_con_medidas_no_toca_la_original(raiz):
    archetipos = prproj_plantilla.archetipos_de_secuencia(raiz)
    grupo_original = prproj_plantilla._video_track_group_de_secuencia(
        raiz, archetipos["4k_9x16"])
    rect_original = grupo_original.find("FrameRect").text
    prproj_generador.clonar_secuencia_con_medidas(
        raiz, archetipos["4k_9x16"], prproj_xml.AsignadorDeIds(raiz),
        nombre="otro", ancho=1080, alto=1920)
    assert grupo_original.find("FrameRect").text == rect_original
