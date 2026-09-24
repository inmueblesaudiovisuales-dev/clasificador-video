import pytest
import base64

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
        ], guia=Guia(orden=["Cocina"]), formato_secuencia="4K 9:16",
        crear_secuencias=True)
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
        ], guia=Guia(orden=["Cocina"]), formato_secuencia="4K 9:16",
        crear_secuencias=True)
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
        "✓ Cocina 01 [SONY]", "Cocina 02 [DRONE]"])


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
