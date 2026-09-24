"""La hoja de Revisar: un proyecto a la vez y su escalera de estado."""
from clasificador_video_portafolio import portafolio as pf
from clasificador_video_portafolio.ui.pantalla_revisar import PantallaRevisar
from PySide6.QtCore import Qt


def _con_un_proyecto(tmp_path):
    p = pf.Portafolio()
    proyecto = p.agregar_proyecto("Casa Reforma", tmp_path / "c.prproj", [])
    proyecto.clips.append(
        pf.ClipDelPortafolio(
            ruta_origen=tmp_path / "clip_014.mov", proyecto="Casa Reforma"
        )
    )
    return p, proyecto


def test_seleccionar_proyecto_en_el_rail_muestra_sus_clips(qtbot, tmp_path):
    p, proyecto = _con_un_proyecto(tmp_path)
    pantalla = PantallaRevisar(p)
    qtbot.addWidget(pantalla)

    pantalla.mostrar_proyecto(proyecto)

    assert pantalla.proyecto_actual is proyecto
    assert len(pantalla.tarjetas) == 1


def test_flecha_arriba_elige_el_clip_actual(qtbot, tmp_path):
    p, proyecto = _con_un_proyecto(tmp_path)
    pantalla = PantallaRevisar(p)
    qtbot.addWidget(pantalla)
    pantalla.mostrar_proyecto(proyecto)

    pantalla.elegir_actual()

    assert proyecto.clips[0].estado == "elegida"


def test_tecla_arriba_en_la_tarjeta_sube_un_peldano(qtbot, tmp_path):
    p, proyecto = _con_un_proyecto(tmp_path)
    pantalla = PantallaRevisar(p)
    qtbot.addWidget(pantalla)
    pantalla.mostrar_proyecto(proyecto)
    pantalla.show()

    qtbot.keyPress(pantalla.tarjetas[0], Qt.Key.Key_Up)

    assert proyecto.clips[0].estado == "elegida"


def test_proyecto_sin_disco_conectado_se_ve_apagado(qtbot, tmp_path):
    p, proyecto = _con_un_proyecto(tmp_path)
    pantalla = PantallaRevisar(p)
    qtbot.addWidget(pantalla)

    assert pantalla.proyecto_disponible(proyecto) is False


def test_ver_rodaje_completo_agrega_solo_las_rutas_faltantes(qtbot, tmp_path):
    carpeta = tmp_path / "rodaje"
    carpeta.mkdir()
    existente = carpeta / "clip_014.mov"
    extra = carpeta / "clip_015.mov"
    existente.touch()
    extra.touch()
    p, proyecto = _con_un_proyecto(tmp_path)
    proyecto.clips[0].ruta_origen = existente
    pantalla = PantallaRevisar(p)
    qtbot.addWidget(pantalla)
    pantalla.mostrar_proyecto(proyecto)

    pantalla.ver_rodaje_completo()

    assert [clip.ruta_origen for clip in proyecto.clips] == [existente, extra]
    assert proyecto.clips[-1].fuera_de_secuencia is True


def test_rodaje_sin_carpeta_deducible_pide_la_carpeta(qtbot, tmp_path):
    p, proyecto = _con_un_proyecto(tmp_path)
    otra = tmp_path / "otra"
    otra.mkdir()
    proyecto.clips.append(pf.ClipDelPortafolio(otra / "otro.mov", proyecto.nombre))
    carpeta = tmp_path / "rodaje"
    carpeta.mkdir()
    extra = carpeta / "extra.mov"
    extra.touch()
    pantalla = PantallaRevisar(p, elegir_carpeta=lambda: carpeta)
    qtbot.addWidget(pantalla)
    pantalla.mostrar_proyecto(proyecto)

    pantalla.ver_rodaje_completo()

    assert any(clip.ruta_origen == extra for clip in proyecto.clips)


def test_rodaje_con_carpeta_deducida_en_ssd_desconectado_pide_carpeta(qtbot, tmp_path):
    p, proyecto = _con_un_proyecto(tmp_path)
    proyecto.clips[0].ruta_origen = tmp_path / "ssd_desconectado" / "clip.mov"
    carpeta = tmp_path / "rodaje"
    carpeta.mkdir()
    extra = carpeta / "extra.mov"
    extra.touch()
    pantalla = PantallaRevisar(p, elegir_carpeta=lambda: carpeta)
    qtbot.addWidget(pantalla)
    pantalla.mostrar_proyecto(proyecto)

    pantalla.ver_rodaje_completo()

    assert any(clip.ruta_origen == extra for clip in proyecto.clips)


def test_categoria_es_editable_desde_revisar(qtbot, tmp_path):
    p, proyecto = _con_un_proyecto(tmp_path)
    pantalla = PantallaRevisar(p)
    qtbot.addWidget(pantalla)
    pantalla.mostrar_proyecto(proyecto)

    pantalla.asignar_categoria_actual("Rancho")

    assert proyecto.categoria == "Rancho"
    assert "Rancho" in p.categorias_conocidas


def test_categoria_nueva_se_guarda_solo_al_confirmar_el_texto_completo(qtbot, tmp_path):
    p, proyecto = _con_un_proyecto(tmp_path)
    pantalla = PantallaRevisar(p)
    qtbot.addWidget(pantalla)
    pantalla.mostrar_proyecto(proyecto)

    pantalla.selector_categoria.setEditText("Ran")

    assert "Ran" not in p.categorias_conocidas
    pantalla.selector_categoria.lineEdit().editingFinished.emit()

    assert proyecto.categoria == "Ran"
    assert "Ran" in p.categorias_conocidas


def test_color_del_proyecto_en_rail_es_estable(qtbot, tmp_path):
    p, proyecto = _con_un_proyecto(tmp_path)
    pantalla = PantallaRevisar(p)
    qtbot.addWidget(pantalla)

    primero = pantalla.color_de_proyecto(proyecto)
    pantalla.actualizar_rail()

    assert pantalla.color_de_proyecto(proyecto) == primero


def test_flechas_izquierda_y_derecha_mueven_el_foco_entre_tarjetas(qtbot, tmp_path):
    p, proyecto = _con_un_proyecto(tmp_path)
    proyecto.clips.append(pf.ClipDelPortafolio(tmp_path / "clip_015.mov", proyecto.nombre))
    pantalla = PantallaRevisar(p)
    qtbot.addWidget(pantalla)
    pantalla.mostrar_proyecto(proyecto)
    pantalla.show()

    qtbot.keyPress(pantalla.tarjetas[0], Qt.Key.Key_Right)

    assert pantalla.tarjetas[1].property("actual") is True


def test_hoja_pide_portadas_solo_para_las_tarjetas_visibles(qtbot, tmp_path, monkeypatch):
    p, proyecto = _con_un_proyecto(tmp_path)
    pantalla = PantallaRevisar(p)
    qtbot.addWidget(pantalla)
    pantalla.mostrar_proyecto(proyecto)
    llamadas = []
    monkeypatch.setattr(pantalla.tarjetas[0], "cargar_miniatura", lambda: llamadas.append(0))

    pantalla._cargar_miniaturas_visibles()

    assert llamadas == [0]
