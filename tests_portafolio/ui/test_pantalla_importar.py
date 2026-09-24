"""La pantalla Importar: soltar proyectos y revisar su vinculación."""
from clasificador_video_portafolio.ui.pantalla_importar import PantallaImportar


def test_arranca_vacia(qtbot):
    pantalla = PantallaImportar()
    qtbot.addWidget(pantalla)

    assert pantalla.filas == []


def test_importar_prproj_agrega_una_fila_y_guarda_el_portafolio(qtbot, tmp_path, monkeypatch):
    destino = tmp_path / "Mi Portafolio.cvportafolio"
    pantalla = PantallaImportar(ruta_portafolio=destino)
    qtbot.addWidget(pantalla)
    ruta = tmp_path / "Casa Reforma.prproj"
    monkeypatch.setattr(
        "clasificador_video_portafolio.ui.pantalla_importar.lector.clips_usados_en",
        lambda _: [],
    )

    pantalla.importar(ruta)

    assert len(pantalla.filas) == 1
    assert "Casa Reforma" in pantalla.filas[0].nombre_visible()
    assert destino.exists()


def test_importar_con_medios_faltantes_lo_señala(qtbot, tmp_path, monkeypatch):
    from clasificador_video_portafolio.lector_de_entregas import ClipUsado

    pantalla = PantallaImportar()
    qtbot.addWidget(pantalla)
    ruta = tmp_path / "Depto Polanco.prproj"
    faltante = ClipUsado(tmp_path / "no_existe.mov", [])
    monkeypatch.setattr(
        "clasificador_video_portafolio.ui.pantalla_importar.lector.clips_usados_en",
        lambda _: [faltante],
    )

    pantalla.importar(ruta)

    assert pantalla.filas[0].tiene_faltantes()
