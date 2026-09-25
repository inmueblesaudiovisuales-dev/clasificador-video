"""La pantalla Armar y entregar: etiquetas de clip, filtro y generar el
.prproj. Hasta la Fase 4.5 NO crea ningún alias de Finder -- solo usa las
rutas que calcula carpetas_de_portafolio. Spec
2026-09-24-modo-portafolio-design.md."""
from PySide6.QtCore import Qt

from clasificador_video_portafolio import portafolio as pf
from clasificador_video_portafolio.ui.pantalla_armar_y_entregar import (
    PantallaArmarYEntregar,
)


def _portafolio(tmp_path):
    p = pf.Portafolio()
    casa = p.agregar_proyecto("Casa Reforma", tmp_path / "casa.prproj", [])
    p.asignar_categoria(casa, "Casa")
    casa.clips.append(pf.ClipDelPortafolio(
        tmp_path / "a.mov", "Casa Reforma", estado="elegida", etiquetas=["Dron"]))
    casa.clips.append(pf.ClipDelPortafolio(
        tmp_path / "b.mov", "Casa Reforma", estado="elegida", etiquetas=["Cocina"]))
    casa.clips.append(pf.ClipDelPortafolio(tmp_path / "c.mov", "Casa Reforma"))
    torre = p.agregar_proyecto("Torre", tmp_path / "torre.prproj", [])
    p.asignar_categoria(torre, "Depto")
    torre.clips.append(pf.ClipDelPortafolio(
        tmp_path / "d.mov", "Torre", estado="elegida", etiquetas=["Dron"]))
    return p


def test_muestra_solo_las_elegidas(qtbot, tmp_path):
    pantalla = PantallaArmarYEntregar(_portafolio(tmp_path))
    qtbot.addWidget(pantalla)

    assert len(pantalla.tarjetas) == 3


def test_agrupa_las_tarjetas_por_proyecto(qtbot, tmp_path):
    pantalla = PantallaArmarYEntregar(_portafolio(tmp_path))
    qtbot.addWidget(pantalla)

    assert set(pantalla.grupos) == {"Casa Reforma", "Torre"}


def test_etiquetas_disponibles_salen_de_las_elegidas(qtbot, tmp_path):
    pantalla = PantallaArmarYEntregar(_portafolio(tmp_path))
    qtbot.addWidget(pantalla)

    assert pantalla.etiquetas_disponibles() == ["Cocina", "Dron"]


def test_filtrar_por_etiqueta_deja_solo_las_que_la_tienen(qtbot, tmp_path):
    pantalla = PantallaArmarYEntregar(_portafolio(tmp_path))
    qtbot.addWidget(pantalla)

    pantalla.alternar_filtro("Dron")

    assert len(pantalla.tarjetas) == 2


def test_alternar_etiqueta_actual_la_suma_y_la_quita(qtbot, tmp_path):
    p = _portafolio(tmp_path)
    pantalla = PantallaArmarYEntregar(p)
    qtbot.addWidget(pantalla)
    clip = p.proyectos[0].clips[0]

    pantalla.alternar_etiqueta_actual("Exteriores")
    assert "Exteriores" in clip.etiquetas

    pantalla.alternar_etiqueta_actual("Exteriores")
    assert "Exteriores" not in clip.etiquetas


def test_tecla_numerica_pone_la_etiqueta_del_rail(qtbot, tmp_path):
    p = _portafolio(tmp_path)
    pantalla = PantallaArmarYEntregar(p)
    qtbot.addWidget(pantalla)
    pantalla.show()

    # Orden alfabético: 1 = Cocina, 2 = Dron
    qtbot.keyPress(pantalla.tarjetas[0], Qt.Key.Key_1)

    assert "Cocina" in p.proyectos[0].clips[0].etiquetas


def test_resumen_cuenta_clips_y_proyectos(qtbot, tmp_path):
    pantalla = PantallaArmarYEntregar(_portafolio(tmp_path))
    qtbot.addWidget(pantalla)

    pantalla.alternar_filtro("Dron")

    resumen = pantalla.resumen()
    assert "2 clips" in resumen
    assert "2 proyectos" in resumen


def test_decidir_etiqueta_guarda_el_portafolio(qtbot, tmp_path):
    destino = tmp_path / "Mi.cvportafolio"
    p = _portafolio(tmp_path)
    pantalla = PantallaArmarYEntregar(p, ruta_portafolio=destino)
    qtbot.addWidget(pantalla)

    pantalla.alternar_etiqueta_actual("Exteriores")

    cargado = pf.Portafolio.cargar(destino)
    assert "Exteriores" in cargado.proyectos[0].clips[0].etiquetas


def test_generar_llama_a_generar_entrega_con_lo_filtrado(qtbot, tmp_path, monkeypatch):
    p = _portafolio(tmp_path)
    carpeta_raiz = tmp_path / "Mi Portafolio"
    pantalla = PantallaArmarYEntregar(p, carpeta_portafolio=carpeta_raiz)
    qtbot.addWidget(pantalla)
    pantalla.alternar_filtro("Dron")
    capturado = {}
    monkeypatch.setattr(
        "clasificador_video_portafolio.ui.pantalla_armar_y_entregar.generar_entrega.generar",
        lambda clips, categorias, carpeta, **resto: capturado.update(
            clips=clips, categorias=categorias, carpeta=carpeta)
        or tmp_path / "x.prproj",
    )

    destino = pantalla.generar()

    assert destino == tmp_path / "x.prproj"
    assert [c.ruta_origen.name for c in capturado["clips"]] == ["a.mov", "d.mov"]
    assert capturado["categorias"] == {"Casa Reforma": "Casa", "Torre": "Depto"}
    assert capturado["carpeta"] == carpeta_raiz


def test_generar_sin_carpeta_la_pide(qtbot, tmp_path, monkeypatch):
    p = _portafolio(tmp_path)
    elegida = tmp_path / "Portafolio elegido"
    pantalla = PantallaArmarYEntregar(p, elegir_carpeta=lambda: elegida)
    qtbot.addWidget(pantalla)
    capturado = {}
    monkeypatch.setattr(
        "clasificador_video_portafolio.ui.pantalla_armar_y_entregar.generar_entrega.generar",
        lambda clips, categorias, carpeta, **resto: capturado.update(carpeta=carpeta)
        or tmp_path / "x.prproj",
    )

    pantalla.generar()

    assert capturado["carpeta"] == elegida
    assert pantalla.carpeta_portafolio == elegida


def test_generar_sin_elegidas_no_hace_nada(qtbot, tmp_path):
    pantalla = PantallaArmarYEntregar(pf.Portafolio(), carpeta_portafolio=tmp_path)
    qtbot.addWidget(pantalla)

    assert pantalla.generar() is None


def test_al_entrar_a_armar_se_crean_los_alias_de_las_elegidas(qtbot, tmp_path, monkeypatch):
    llamadas = []
    monkeypatch.setattr(
        "clasificador_video_portafolio.ui.pantalla_armar_y_entregar.caf.crear",
        lambda origen, destino: llamadas.append((origen, destino)),
    )
    p = pf.Portafolio()
    casa = p.agregar_proyecto("Casa Reforma", tmp_path / "casa.prproj", [])
    casa.clips.append(pf.ClipDelPortafolio(
        tmp_path / "a.mov", "Casa Reforma", estado="elegida"))
    carpeta_raiz = tmp_path / "Mi Portafolio"

    pantalla = PantallaArmarYEntregar(p, carpeta_portafolio=carpeta_raiz)
    qtbot.addWidget(pantalla)

    assert llamadas == [
        (tmp_path / "a.mov", carpeta_raiz / "Casa Reforma" / "a.mov"),
    ]


def test_sin_carpeta_elegida_no_intenta_crear_alias(qtbot, tmp_path, monkeypatch):
    llamadas = []
    monkeypatch.setattr(
        "clasificador_video_portafolio.ui.pantalla_armar_y_entregar.caf.crear",
        lambda origen, destino: llamadas.append((origen, destino)),
    )

    pantalla = PantallaArmarYEntregar(_portafolio(tmp_path))
    qtbot.addWidget(pantalla)

    assert llamadas == []


def test_refrescar_no_repite_alias_ya_creados(qtbot, tmp_path, monkeypatch):
    llamadas = []
    monkeypatch.setattr(
        "clasificador_video_portafolio.ui.pantalla_armar_y_entregar.caf.crear",
        lambda origen, destino: llamadas.append((origen, destino)),
    )
    p = pf.Portafolio()
    casa = p.agregar_proyecto("Casa Reforma", tmp_path / "casa.prproj", [])
    casa.clips.append(pf.ClipDelPortafolio(
        tmp_path / "a.mov", "Casa Reforma", estado="elegida"))
    carpeta_raiz = tmp_path / "Mi Portafolio"
    pantalla = PantallaArmarYEntregar(p, carpeta_portafolio=carpeta_raiz)
    qtbot.addWidget(pantalla)

    pantalla.alternar_filtro("cualquiera")

    assert len(llamadas) == 2


def test_falla_al_crear_un_alias_no_bloquea_los_demas(qtbot, tmp_path, monkeypatch):
    llamadas = []

    def crear_falso(origen, destino):
        if origen.name == "a.mov":
            raise OSError("disco desconectado")
        llamadas.append((origen, destino))

    monkeypatch.setattr(
        "clasificador_video_portafolio.ui.pantalla_armar_y_entregar.caf.crear",
        crear_falso,
    )
    p = pf.Portafolio()
    casa = p.agregar_proyecto("Casa Reforma", tmp_path / "casa.prproj", [])
    casa.clips.append(pf.ClipDelPortafolio(
        tmp_path / "a.mov", "Casa Reforma", estado="elegida"))
    casa.clips.append(pf.ClipDelPortafolio(
        tmp_path / "b.mov", "Casa Reforma", estado="elegida"))

    pantalla = PantallaArmarYEntregar(p, carpeta_portafolio=tmp_path / "Mi Portafolio")
    qtbot.addWidget(pantalla)

    assert [origen.name for origen, _ in llamadas] == ["b.mov"]
