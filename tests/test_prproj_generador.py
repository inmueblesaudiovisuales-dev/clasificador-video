import pytest
import base64
import os
import xml.etree.ElementTree as ET
from pathlib import Path

from clasificador_video import prproj_generador, prproj_plantilla, prproj_xml, recursos

TICKS_POR_SEGUNDO = prproj_generador.TICKS_POR_SEGUNDO


@pytest.fixture
def raiz(): return prproj_xml.leer_prproj(recursos.template_color_luts())


def _probe_falso(fps=59.94, duration_seconds=6.006, rotation=0):
    return {"fps": fps, "duration_seconds": duration_seconds, "rotation": rotation, "width": 1080, "height": 1920}


def _resolver(raiz, elemento):
    """Objeto de raíz al que apunta la referencia de un Item visible."""
    referencia = elemento.get("ObjectURef") or elemento.get("ObjectRef")
    if referencia is None:
        return None
    return next(
        (c for c in raiz
         if c.get("ObjectUID") == referencia or c.get("ObjectID") == referencia),
        None)


def _items_visibles(raiz, contenedor):
    items = contenedor.find("ProjectItemContainer/Items")
    return list(items) if items is not None else []


def _nombre_de(raiz, elemento):
    objeto = _resolver(raiz, elemento)
    nombre = objeto.find(".//Name") if objeto is not None else None
    return nombre.text if nombre is not None else None


def _arbol_visible(raiz):
    """Recorre SOLO el árbol visible de ``ProjectItemContainer/Items``."""
    def recorrer(contenedor):
        ramas = []
        for item in _items_visibles(raiz, contenedor):
            objeto = _resolver(raiz, item)
            if objeto is None:
                continue
            rama = {"nombre": _nombre_de(raiz, item), "tag": objeto.tag,
                    "objeto": objeto, "hijos": []}
            if objeto.tag == "BinProjectItem":
                rama["hijos"] = recorrer(objeto)
            ramas.append(rama)
        return ramas
    return recorrer(raiz.find("RootProjectItem"))


def _aplanar(arbol):
    for rama in arbol:
        yield rama
        yield from _aplanar(rama["hijos"])


def _clip_items_visibles(raiz):
    clip = next(rama for rama in _arbol_visible(raiz)
                if rama["nombre"] == "02. Clip")
    return [rama["objeto"] for rama in _aplanar(clip["hijos"])
            if rama["tag"] == "ClipProjectItem"]


def _fuente_de_item(raiz, item, tag):
    master = next(m for m in raiz.findall("MasterClip")
                  if m.get("ObjectUID") == item.find("MasterClip").get("ObjectURef"))
    for clip_ref in master.findall("Clips/Clip"):
        clip = next(c for c in raiz if c.get("ObjectID") == clip_ref.get("ObjectRef"))
        if clip.tag != tag:
            continue
        return next(c for c in raiz if c.get("ObjectID") == clip.find("Clip/Source").get("ObjectRef"))


def _proxy_de_video(raiz, item):
    fuente = _fuente_de_item(raiz, item, "VideoClip")
    referencia = fuente.find("MediaSource/Content/ProxyMedia")
    return (next((m for m in raiz.findall("Media")
                  if m.get("ObjectUID") == referencia.get("ObjectURef")), None)
            if referencia is not None else None)


def _audio_proxies_de(raiz, item):
    fuente = _fuente_de_item(raiz, item, "AudioClip")
    return fuente.findall("MediaSource/Content/AudioProxies/AudioProxyItem")


def _ruta_de(media):
    return media.findtext("FilePath")


def _tracks_de_secuencia(raiz, secuencia):
    """Los objetos de track colgados del ``VideoTrackGroup``/``AudioTrackGroup``."""
    tracks = []
    for grupo_ref in secuencia.findall(".//TrackGroup/Second"):
        grupo = next(
            (c for c in raiz if c.get("ObjectID") == grupo_ref.get("ObjectRef")),
            None)
        if grupo is None:
            continue
        for track_ref in grupo.findall(".//Track"):
            track = next(
                (c for c in raiz if c.get("ObjectUID") == track_ref.get("ObjectURef")),
                None)
            if track is not None:
                tracks.append(track)
    return tracks


def _generar_proyecto_de_prueba(tmp_path):
    from clasificador_video.manifest import Clip, Guia, Manifest

    manifest = Manifest(
        proyecto="IAV-2609.10-A", orientacion="vertical",
        clips=[
            Clip(orden=0, ruta=tmp_path / "sony1.mp4",
                 categoria_path=["Cocina"], fps=59.94, flag="pick",
                 camara="sony", bin_sony=True),
            Clip(orden=1, ruta=tmp_path / "dron1.mp4",
                 categoria_path=["Cocina"], fps=59.94, flag="none",
                 camara="dji", bin_dron=True),
        ], guia=Guia(orden=["Cocina"]))
    for clip in manifest.clips:
        clip.ruta.write_bytes(b"")
    destino = tmp_path / "salida" / "IAV-2609.10-A.prproj"
    carpeta_luts = tmp_path / "salida" / "01. Proyecto premiere" / "LUTs"

    def probe_falso(_ruta):
        return {"width": 2160, "height": 3840, "fps": 59.94,
                "duration_seconds": 6.0, "rotation": 90}

    prproj_generador.generar_prproj(
        manifest, destino, carpeta_luts, probe=probe_falso)
    return destino, carpeta_luts, manifest


def _generar_proyecto_con_proxy(tmp_path, ruta_proxy, datos_proxy=None):
    from clasificador_video.manifest import Clip, Guia, Manifest

    original_con_proxy = tmp_path / "con_proxy.mp4"
    original_sin_proxy = tmp_path / "sin_proxy.mp4"
    original_con_proxy.write_bytes(b"")
    original_sin_proxy.write_bytes(b"")
    manifest = Manifest(
        proyecto="Proxies", orientacion="vertical", clips=[
            Clip(orden=0, ruta=original_con_proxy, ruta_proxy=ruta_proxy,
                 categoria_path=["Cocina"], fps=59.94, camara="sony"),
            Clip(orden=1, ruta=original_sin_proxy, categoria_path=["Cocina"],
                 fps=59.94, camara="sony"),
        ], guia=Guia(orden=["Cocina"]))
    destino = tmp_path / "salida" / "proxies.prproj"
    datos = {"width": 2160, "height": 3840, "fps": 59.94,
             "duration_seconds": 6.0, "rotation": 90}
    prproj_generador.generar_prproj(
        manifest, destino, tmp_path / "luts",
        probe=lambda ruta: datos_proxy if ruta == ruta_proxy and datos_proxy else datos)
    return prproj_xml.leer_prproj(destino)


def test_generar_prproj_adjunta_proxy_real_sin_crear_otro_clip_visible(tmp_path):
    proxy = tmp_path / "con_proxy_proxy.mp4"
    proxy.write_bytes(b"")

    raiz = _generar_proyecto_con_proxy(tmp_path, proxy)
    con_proxy, sin_proxy = _clip_items_visibles(raiz)

    assert _proxy_de_video(raiz, con_proxy).find("IsProxy").text == "true"
    assert _ruta_de(_proxy_de_video(raiz, con_proxy)) == str(proxy)
    assert _proxy_de_video(raiz, sin_proxy) is None
    assert len(_clip_items_visibles(raiz)) == 2
    assert _audio_proxies_de(raiz, con_proxy)


def test_generar_prproj_el_proxy_no_comparte_identidad_con_el_original(tmp_path):
    proxy = tmp_path / "con_proxy_proxy.mp4"
    proxy.write_bytes(b"")

    raiz = _generar_proyecto_con_proxy(tmp_path, proxy)
    item = _clip_items_visibles(raiz)[0]
    media_proxy = _proxy_de_video(raiz, item)
    # El original del mismo clip es el otro Media del proyecto.
    medias = raiz.findall("Media")
    media_original = next(m for m in medias if m is not media_proxy)

    assert media_proxy.find("FileKey").text != media_original.find("FileKey").text
    assert media_proxy.find("FileKey").text != "00000000-0000-0000-0000-000000000000"


def test_generar_prproj_omite_proxy_cuya_ruta_no_existe(tmp_path):
    raiz = _generar_proyecto_con_proxy(tmp_path, tmp_path / "no-existe_proxy.mp4")

    assert _proxy_de_video(raiz, _clip_items_visibles(raiz)[0]) is None


def test_generar_prproj_acepta_proxy_s03_de_menor_resolucion(tmp_path):
    proxy = tmp_path / "con_proxyS03.mp4"
    proxy.write_bytes(b"")

    raiz = _generar_proyecto_con_proxy(
        tmp_path, proxy,
        {"width": 1080, "height": 1920, "fps": 59.94,
         "duration_seconds": 6.0, "rotation": 0})

    assert _proxy_de_video(raiz, _clip_items_visibles(raiz)[0]) is not None


def test_reescribir_rutas_de_media_reemplaza_todas_las_copias():
    ruta = Path("/media/nueva/toma_proxy.mp4")
    media = ET.fromstring("""
        <Media><RelativePath>../vieja/a.mp4</RelativePath>
        <RelativePath>../vieja/b.mp4</RelativePath><FilePath>/vieja/a.mp4</FilePath>
        <FilePath>/vieja/b.mp4</FilePath><ActualMediaFilePath>/vieja/a.mp4</ActualMediaFilePath>
        <ActualMediaFilePath>/vieja/b.mp4</ActualMediaFilePath><Title>vieja.mp4</Title></Media>""")

    prproj_generador._reescribir_rutas_de_media(media, ruta)

    assert {n.text for n in media.findall("RelativePath")} == {"../media/nueva/toma_proxy.mp4"}
    assert {n.text for n in media.findall("FilePath")} == {str(ruta)}
    assert {n.text for n in media.findall("ActualMediaFilePath")} == {str(ruta)}
    assert {n.text for n in media.findall("Title")} == {ruta.name}


def test_proyecto_generado_calcula_relative_path_desde_su_carpeta(tmp_path):
    proxy = tmp_path / "con_proxyS03.mp4"
    proxy.write_bytes(b"")

    raiz = _generar_proyecto_con_proxy(tmp_path, proxy)
    media_proxy = _proxy_de_video(raiz, _clip_items_visibles(raiz)[0])
    carpeta_prproj = tmp_path / "salida"

    assert media_proxy.findtext("RelativePath") == os.path.relpath(
        proxy, carpeta_prproj)


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


def test_clonar_clip_tambien_renombra_el_master_clip(raiz, tmp_path):
    """Premiere lee el nombre del MasterClip, no solo el del ClipProjectItem.

    Comprobado contra `TemplateColorLuts.prproj`: el MasterClip tiene su
    PROPIO `Name`, separado del `ProjectItem/Node/Name` del item visible.
    Si solo se cambia el del item, el XML dice `COCINA-01` en un lugar y
    el nombre viejo del archivo en otro -- justo el síntoma reportado.
    """
    a = prproj_plantilla.archetipos_de_clip(raiz)
    clon = prproj_generador.clonar_clip(
        raiz, a['sony'], prproj_xml.AsignadorDeIds(raiz),
        ruta_archivo=tmp_path / 'c.mp4', nombre_en_premiere='COCINA-01 [SONY]',
        label_name='x', label_color=1, datos_probe=_probe_falso())
    master = raiz.find(f'.//MasterClip[@ObjectUID="{clon.master_clip_uid}"]')
    assert master.find('Name').text == 'COCINA-01 [SONY]'


def test_clonar_clip_le_da_a_cada_media_su_propio_identificador(raiz, tmp_path):
    """Dos clips clonados no pueden compartir FileKey ni ContentAndMetadataState.

    Comprobado contra un proyecto real de Premiere (`despues.prproj`,
    2026-09-24): el original y su proxy llevan cada uno un GUID distinto
    en esos dos campos. La plantilla los trae sanitizados al mismo valor
    fijo para poder versionarla; sin regenerarlos, dos archivos distintos
    terminaban con la misma identidad.
    """
    ids = prproj_xml.AsignadorDeIds(raiz)
    a = prproj_plantilla.archetipos_de_clip(raiz)
    c1 = prproj_generador.clonar_clip(
        raiz, a['sony'], ids, ruta_archivo=tmp_path / 'a.mp4',
        nombre_en_premiere='a', label_name='x', label_color=1,
        datos_probe=_probe_falso())
    c2 = prproj_generador.clonar_clip(
        raiz, a['sony'], ids, ruta_archivo=tmp_path / 'b.mp4',
        nombre_en_premiere='b', label_name='x', label_color=1,
        datos_probe=_probe_falso())
    def _media_con_file_key(ruta_archivo):
        return next(
            m for m in raiz.findall('Media')
            if m.find('FileKey') is not None
            and (p := m.find('FilePath')) is not None
            and p.text == str(ruta_archivo))

    m1 = _media_con_file_key(tmp_path / 'a.mp4')
    m2 = _media_con_file_key(tmp_path / 'b.mp4')
    assert m1.find('FileKey').text != m2.find('FileKey').text
    assert m1.find('ContentAndMetadataState').text != m2.find(
        'ContentAndMetadataState').text
    estado = m1.find('ContentAndMetadataState').text
    assert base64.b64decode(
        m1.find('ModificationState').text).decode('utf-16-le') == estado


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


def _secuencia_de_item(raiz, item):
    master = next(m for m in raiz.findall("MasterClip")
                  if m.get("ObjectUID") == item.find("MasterClip").get("ObjectURef"))
    for clip_ref in master.findall("Clips/Clip"):
        clip = next(c for c in raiz if c.get("ObjectID") == clip_ref.get("ObjectRef"))
        if clip.tag != "VideoClip":
            continue
        fuente_ref = clip.find("Clip/Source")
        fuente = next(c for c in raiz if c.get("ObjectID") == fuente_ref.get("ObjectRef"))
        return next(s for s in raiz.findall("Sequence")
                    if s.get("ObjectUID")
                    == fuente.find("SequenceSource/Sequence").get("ObjectURef"))


def test_clonar_secuencia_con_medidas_le_pone_el_nombre(raiz):
    arquetipo = prproj_plantilla.archetipo_de_secuencia(raiz)
    item = prproj_generador.clonar_secuencia_con_medidas(
        raiz, arquetipo, prproj_xml.AsignadorDeIds(raiz),
        nombre="IAV-2609.10-A 4K 9:16")
    assert item.tag == "ClipProjectItem"
    assert item.find(".//Name").text == "IAV-2609.10-A 4K 9:16"
    assert _secuencia_de_item(raiz, item).find("Name").text == "IAV-2609.10-A 4K 9:16"


def test_clonar_secuencia_con_medidas_voltea_para_16x9(raiz):
    arquetipo = prproj_plantilla.archetipo_de_secuencia(raiz)
    item = prproj_generador.clonar_secuencia_con_medidas(
        raiz, arquetipo, prproj_xml.AsignadorDeIds(raiz),
        nombre="x 4K 16:9", ancho=3840, alto=2160)
    grupo = prproj_plantilla._video_track_group_de_secuencia(
        raiz, _secuencia_de_item(raiz, item))
    assert grupo.find("FrameRect").text == "0,0,3840,2160"


def test_clonar_secuencia_con_medidas_no_toca_la_original(raiz):
    arquetipo = prproj_plantilla.archetipo_de_secuencia(raiz)
    original = next(s for s in raiz.findall("Sequence")
                    if s.get("ObjectUID") == arquetipo.sequence_uid)
    grupo_original = prproj_plantilla._video_track_group_de_secuencia(raiz, original)
    rect_original = grupo_original.find("FrameRect").text
    prproj_generador.clonar_secuencia_con_medidas(
        raiz, arquetipo, prproj_xml.AsignadorDeIds(raiz),
        nombre="otro", ancho=1080, alto=1920)
    assert grupo_original.find("FrameRect").text == rect_original


def test_crear_bin_hijo_lo_agrega_al_container_del_padre(raiz):
    arquetipo_bin = prproj_plantilla.archetipo_de_bin(raiz)
    padre = raiz.find("RootProjectItem")
    bin_nuevo = prproj_generador.crear_bin_hijo(
        raiz, arquetipo_bin, padre, prproj_xml.AsignadorDeIds(raiz),
        nombre="02. Clip")
    assert bin_nuevo.find(".//Name").text == "02. Clip"
    items = padre.find("ProjectItemContainer/Items")
    refs = [item.get("ObjectURef") or item.get("ObjectRef") for item in items]
    assert (bin_nuevo.get("ObjectUID") or bin_nuevo.get("ObjectID")) in refs


def test_arbol_de_bins_crea_las_7_carpetas_fijas(raiz):
    arquetipo_bin = prproj_plantilla.archetipo_de_bin(raiz)
    bins = prproj_generador.crear_esqueleto(
        raiz, arquetipo_bin, raiz.find("RootProjectItem"),
        prproj_xml.AsignadorDeIds(raiz))
    assert list(bins) == [
        "01. Secuencia", "02. Clip", "03. AE composition", "04. Musica",
        "05. Voz", "06. Graficos", "07. Assets adicionales"]


def test_bin_del_cuarto_numera_y_marca_camara(raiz):
    arquetipo_bin = prproj_plantilla.archetipo_de_bin(raiz)
    asignador = prproj_xml.AsignadorDeIds(raiz)
    bins = prproj_generador.crear_esqueleto(
        raiz, arquetipo_bin, raiz.find("RootProjectItem"), asignador)
    clips = [{"categoria_path": ["Cocina"], "bin_sony": True,
              "bin_dron": False, "bin_pocket": False}]
    bin_cuarto = prproj_generador.bin_del_cuarto(
        raiz, arquetipo_bin, bins["02. Clip"], asignador,
        categoria_path=["Cocina"], posicion=3, clips_del_manifest=clips)
    assert bin_cuarto.find(".//Name").text == "03. Cocina [SONY]"


def test_generar_prproj_produce_un_archivo_que_se_puede_releer(tmp_path):
    from clasificador_video.manifest import Clip, Guia, Manifest

    manifest = Manifest(
        proyecto="IAV-2609.10-A", orientacion="vertical",
        clips=[
            Clip(orden=0, ruta=tmp_path / "sony1.mp4",
                 categoria_path=["Cocina"], fps=59.94, flag="pick",
                 camara="sony", bin_sony=True),
            Clip(orden=1, ruta=tmp_path / "dron1.mp4",
                 categoria_path=["Cocina"], fps=59.94, flag="none",
                 camara="dji", bin_dron=True),
        ], guia=Guia(orden=["Cocina"]))
    for clip in manifest.clips:
        clip.ruta.write_bytes(b"")
    destino = tmp_path / "salida" / "IAV-2609.10-A.prproj"
    carpeta_luts = tmp_path / "salida" / "01. Proyecto premiere" / "LUTs"

    def probe_falso(_ruta):
        return {"width": 2160, "height": 3840, "fps": 59.94,
                "duration_seconds": 6.0, "rotation": 90}

    prproj_generador.generar_prproj(
        manifest, destino, carpeta_luts, probe=probe_falso)

    assert destino.is_file()
    raiz = prproj_xml.leer_prproj(destino)
    assert len(raiz.findall("ClipProjectItem")) >= 2 + 3
    valores_lut = []
    for valor in raiz.iter("StartKeyframeValue"):
        try:
            valores_lut.append(base64.b64decode(
                (valor.text or "").strip()).decode("utf-16-le").rstrip("\0"))
        except UnicodeDecodeError:
            pass
    assert str(carpeta_luts / "SONY-SLOG3.cube") in valores_lut
    assert str(carpeta_luts / "DJI-DLOGM.cube") in valores_lut


def test_arbol_visible_solo_tiene_los_siete_bins_en_orden(tmp_path):
    destino, _luts, _manifest = _generar_proyecto_de_prueba(tmp_path)
    raiz = prproj_xml.leer_prproj(destino)
    arbol = _arbol_visible(raiz)
    assert [rama["nombre"] for rama in arbol] == list(
        prproj_generador.CARPETAS_DEL_PROYECTO)
    assert all(rama["tag"] == "BinProjectItem" for rama in arbol)


def test_arbol_visible_no_conserva_items_de_la_plantilla(tmp_path):
    destino, _luts, _manifest = _generar_proyecto_de_prueba(tmp_path)
    raiz = prproj_xml.leer_prproj(destino)
    nombres = {rama["nombre"] for rama in _aplanar(_arbol_visible(raiz))}
    assert "Bin" not in nombres
    for referencia in (
            "20260910_PIB0001.MP4", "DJI_20260910113520_0008_D.MP4",
            "20260910_PIB0002.MP4"):
        assert referencia not in nombres


def test_arbol_visible_no_tiene_clips_ni_secuencias_en_la_raiz(tmp_path):
    destino, _luts, _manifest = _generar_proyecto_de_prueba(tmp_path)
    raiz = prproj_xml.leer_prproj(destino)
    arbol = _arbol_visible(raiz)
    assert not [rama for rama in arbol
                if rama["tag"] in ("ClipProjectItem", "Sequence")]


def test_02_clip_solo_tiene_los_clips_del_manifest(tmp_path):
    destino, _luts, _manifest = _generar_proyecto_de_prueba(tmp_path)
    raiz = prproj_xml.leer_prproj(destino)
    arbol = _arbol_visible(raiz)
    clip = next(rama for rama in arbol if rama["nombre"] == "02. Clip")
    visibles = list(_aplanar(clip["hijos"]))
    assert all(rama["tag"] in ("BinProjectItem", "ClipProjectItem")
               for rama in visibles)
    clips = [rama for rama in visibles if rama["tag"] == "ClipProjectItem"]
    assert sorted(rama["nombre"] for rama in clips) == sorted([
        "COCINA-01 ✓ [SONY]", "COCINA-02 [DRONE]"])


def test_01_secuencia_tiene_las_cinco_secuencias_en_su_lugar(tmp_path):
    destino, _luts, _manifest = _generar_proyecto_de_prueba(tmp_path)
    raiz = prproj_xml.leer_prproj(destino)
    arbol = _arbol_visible(raiz)
    sec = next(rama for rama in arbol if rama["nombre"] == "01. Secuencia")
    hijos = sec["hijos"]
    assert [h["nombre"] for h in hijos] == [
        prproj_generador.CARPETA_RESOLUCION_ORIGINAL,
        prproj_generador.CARPETA_1080P]
    assert all(h["tag"] == "BinProjectItem" for h in hijos)
    assert [h["nombre"] for h in hijos[0]["hijos"]] == [
        "IAV-2609.10-A 4K 9:16", "IAV-2609.10-A 2.7K 9:16",
        "IAV-2609.10-A 4K 16:9"]
    assert [h["nombre"] for h in hijos[1]["hijos"]] == [
        "IAV-2609.10-A 9:16 1080p", "IAV-2609.10-A 16:9 1080p"]


def test_secuencias_tienen_sus_medidas_y_fps(tmp_path):
    destino, _luts, _manifest = _generar_proyecto_de_prueba(tmp_path)
    raiz = prproj_xml.leer_prproj(destino)
    arbol = _arbol_visible(raiz)
    esperado = {
        "IAV-2609.10-A 4K 9:16": (2160, 3840),
        "IAV-2609.10-A 2.7K 9:16": (1512, 2688),
        "IAV-2609.10-A 4K 16:9": (3840, 2160),
        "IAV-2609.10-A 9:16 1080p": (1080, 1920),
        "IAV-2609.10-A 16:9 1080p": (1920, 1080),
    }
    items = [rama for rama in _aplanar(arbol)
             if rama["nombre"] in esperado]
    assert len(items) == 5
    for rama in items:
        secuencia = _secuencia_de_item(raiz, rama["objeto"])
        grupo = prproj_plantilla._video_track_group_de_secuencia(raiz, secuencia)
        ancho, alto = esperado[rama["nombre"]]
        assert grupo.find("FrameRect").text == f"0,0,{ancho},{alto}"
        fps = TICKS_POR_SEGUNDO / int(grupo.find(".//FrameRate").text)
        assert abs(fps - 59.94) < 0.01


def test_secuencias_generadas_estan_vacias(tmp_path):
    destino, _luts, _manifest = _generar_proyecto_de_prueba(tmp_path)
    raiz = prproj_xml.leer_prproj(destino)
    arbol = _arbol_visible(raiz)
    sec = next(rama for rama in arbol if rama["nombre"] == "01. Secuencia")
    for rama in _aplanar(sec["hijos"]):
        if rama["tag"] != "ClipProjectItem":
            continue
        secuencia = _secuencia_de_item(raiz, rama["objeto"])
        for track in _tracks_de_secuencia(raiz, secuencia):
            assert track.findall(".//TrackItem") == []


def _blob_de_cadena(raiz, chain_id):
    indice = {e.get("ObjectID"): e for e in raiz if e.get("ObjectID")}
    pendientes, vistos = [chain_id], set()
    while pendientes:
        ident = pendientes.pop()
        if ident in vistos or ident not in indice:
            continue
        vistos.add(ident)
        nodo = indice[ident]
        if nodo.tag == "ArbVideoComponentParam" \
                and (nodo.findtext("Name") or "").strip() == "Blob":
            valor = nodo.find("StartKeyframeValue")
            return base64.b64decode(
                (valor.text or "").strip()).decode("utf-8", errors="ignore")
        pendientes.extend(
            h.get("ObjectRef") for h in nodo.iter() if h.get("ObjectRef"))
    return None


def test_lut_sony_apunta_a_la_copia_local_dentro_del_blob(tmp_path):
    original = prproj_plantilla.archetipos_de_clip(
        prproj_xml.leer_prproj(recursos.template_color_luts()))["sony"].ruta_lut
    destino, luts, _manifest = _generar_proyecto_de_prueba(tmp_path)
    raiz = prproj_xml.leer_prproj(destino)
    arquetipo = prproj_plantilla.archetipos_de_clip(raiz)["sony"]
    blob = _blob_de_cadena(raiz, arquetipo.video_component_chain_id)
    assert blob is not None
    assert str(luts / "SONY-SLOG3.cube") in blob
    assert original not in blob


def test_arbol_visible_completo_replica_la_estructura_de_clipify(tmp_path):
    original = prproj_plantilla.archetipos_de_clip(
        prproj_xml.leer_prproj(recursos.template_color_luts()))["sony"].ruta_lut
    destino, luts, _manifest = _generar_proyecto_de_prueba(tmp_path)
    raiz = prproj_xml.leer_prproj(destino)
    arbol = _arbol_visible(raiz)
    plano = list(_aplanar(arbol))
    nombres = {rama["nombre"] for rama in plano}

    # Raíz: exactamente los siete bins, sin items de plantilla.
    assert [rama["nombre"] for rama in arbol] == list(
        prproj_generador.CARPETAS_DEL_PROYECTO)
    assert "Bin" not in nombres
    for referencia in ("20260910_PIB0001.MP4", "DJI_20260910113520_0008_D.MP4",
                       "20260910_PIB0002.MP4"):
        assert referencia not in nombres
    assert not [rama for rama in arbol
                if rama["tag"] in ("ClipProjectItem", "Sequence")]

    # 01. Secuencia: el bin de resoluciones originales y el sub-bin 1080p.
    secuencia = next(rama for rama in arbol if rama["nombre"] == "01. Secuencia")
    assert [h["nombre"] for h in secuencia["hijos"]] == [
        prproj_generador.CARPETA_RESOLUCION_ORIGINAL,
        prproj_generador.CARPETA_1080P]
    assert [h["nombre"] for h in secuencia["hijos"][0]["hijos"]] == [
        "IAV-2609.10-A 4K 9:16", "IAV-2609.10-A 2.7K 9:16",
        "IAV-2609.10-A 4K 16:9"]
    assert [h["nombre"] for h in secuencia["hijos"][1]["hijos"]] == [
        "IAV-2609.10-A 9:16 1080p", "IAV-2609.10-A 16:9 1080p"]

    # 02. Clip: solo los clips del manifest.
    clip = next(rama for rama in arbol if rama["nombre"] == "02. Clip")
    assert sorted(rama["nombre"] for rama in _aplanar(clip["hijos"])
                  if rama["tag"] == "ClipProjectItem") == sorted([
        "COCINA-01 ✓ [SONY]", "COCINA-02 [DRONE]"])

    # LUT Sony: en el componente efectivo y con el archivo empaquetado.
    assert (luts / "SONY-SLOG3.cube").is_file()
    arquetipo = prproj_plantilla.archetipos_de_clip(raiz)["sony"]
    blob = _blob_de_cadena(raiz, arquetipo.video_component_chain_id)
    assert str(luts / "SONY-SLOG3.cube") in blob
    assert original not in blob


def test_generar_prproj_ordena_bien_un_cuarto_con_mas_de_99_clips(tmp_path):
    from clasificador_video.manifest import Clip, Guia, Manifest

    clips = []
    for i in range(101):
        ruta = tmp_path / f"c{i}.mp4"
        ruta.write_bytes(b"")
        clips.append(Clip(orden=i, ruta=ruta, categoria_path=["Cocina"],
                           fps=59.94, camara="sony"))
    manifest = Manifest(proyecto="Cien", orientacion="horizontal", clips=clips,
                        guia=Guia(orden=["Cocina"]))
    destino = tmp_path / "salida" / "cien.prproj"

    def probe_falso(_ruta):
        return {"width": 1920, "height": 1080, "fps": 59.94,
                "duration_seconds": 1.0, "rotation": 0}

    prproj_generador.generar_prproj(
        manifest, destino, tmp_path / "luts", probe=probe_falso)
    raiz = prproj_xml.leer_prproj(destino)
    clip = next(rama for rama in _arbol_visible(raiz) if rama["nombre"] == "02. Clip")
    nombres = sorted(rama["nombre"] for rama in _aplanar(clip["hijos"])
                      if rama["tag"] == "ClipProjectItem")
    assert len(nombres) == 101
    assert nombres[0] == "COCINA-001"
    assert nombres[1] == "COCINA-002"
    assert nombres[-1] == "COCINA-101"


def test_ruta_libre_con_version_no_cambia_si_no_existe(tmp_path):
    destino = tmp_path / "IAV-2609.10-A.prproj"
    assert prproj_generador.ruta_libre_con_version(destino) == destino


def test_ruta_libre_con_version_salta_a_v2_y_luego_v3(tmp_path):
    destino = tmp_path / "IAV-2609.10-A.prproj"
    destino.write_bytes(b"original")
    v2 = tmp_path / "IAV-2609.10-A v2.prproj"
    assert prproj_generador.ruta_libre_con_version(destino) == v2
    v2.write_bytes(b"v2")
    assert prproj_generador.ruta_libre_con_version(destino) == (
        tmp_path / "IAV-2609.10-A v3.prproj")
    assert destino.read_bytes() == b"original"


def test_generar_prproj_copia_solo_los_cube_que_hacen_falta(tmp_path):
    from clasificador_video.manifest import Clip, Manifest

    manifest = Manifest(
        proyecto="Solo Sony", orientacion="horizontal",
        clips=[Clip(orden=0, ruta=tmp_path / "a.mp4",
                    categoria_path=["Sala"], fps=59.94, camara="sony")])
    manifest.clips[0].ruta.write_bytes(b"")
    destino = tmp_path / "s" / "p.prproj"
    carpeta_luts = tmp_path / "s" / "01. Proyecto premiere" / "LUTs"

    def probe_falso(_ruta):
        return {"width": 1920, "height": 1080, "fps": 59.94,
                "duration_seconds": 3.0, "rotation": 0}

    prproj_generador.generar_prproj(
        manifest, destino, carpeta_luts, probe=probe_falso)

    assert (carpeta_luts / "SONY-SLOG3.cube").is_file()
    assert not (carpeta_luts / "DJI-DLOGM.cube").is_file()
