# tests/ui/test_pantalla_inicio.py
from pathlib import Path

from clasificador_video.recientes import Reciente
from clasificador_video.ui.pantalla_inicio import PantallaInicio


def test_lista_los_recientes_con_el_mas_nuevo_arriba(qtbot):
    pantalla = PantallaInicio()
    qtbot.addWidget(pantalla)
    pantalla.set_recientes([
        Reciente(Path("/a/dos.cvproj"), "Dos", "2026-08-09 10:00"),
        Reciente(Path("/a/uno.cvproj"), "Uno", "2026-08-08 09:00"),
    ])

    assert pantalla.nombres_visibles() == ["Dos", "Uno"]


def test_un_proyecto_que_no_esta_se_ve_apagado_y_no_abre(qtbot, tmp_path):
    """Se muestra en vez de podarse: Bruno tiene que ver que el proyecto
    existio y que el disco no esta conectado, no que desaparecio."""
    pantalla = PantallaInicio()
    qtbot.addWidget(pantalla)
    pantalla.set_recientes([Reciente(tmp_path / "no-esta.cvproj", "Fantasma", "")])
    abiertos = []
    pantalla.abrir_pedido.connect(abiertos.append)

    fila = pantalla.filas[0]
    assert not fila.isEnabled()
    fila.click()
    assert abiertos == []


def test_el_apagado_dice_por_que_no_abre(qtbot, tmp_path):
    """No basta con verse gris: si no dice nada, Bruno no sabe si el
    proyecto se rompio o si solo falta conectar el disco."""
    pantalla = PantallaInicio()
    qtbot.addWidget(pantalla)
    pantalla.set_recientes([Reciente(tmp_path / "no-esta.cvproj", "Fantasma", "")])

    assert "No se encuentra" in pantalla.filas[0].detalle.full_text()


def test_uno_que_si_esta_abre_con_su_ruta(qtbot, tmp_path):
    archivo = tmp_path / "Casa Lomas.cvproj"
    archivo.write_text("{}")
    pantalla = PantallaInicio()
    qtbot.addWidget(pantalla)
    pantalla.set_recientes([Reciente(archivo, "Casa Lomas", "2026-08-09 10:00")])
    abiertos = []
    pantalla.abrir_pedido.connect(abiertos.append)

    pantalla.filas[0].click()

    assert abiertos == [archivo]


def test_los_botones_avisan(qtbot):
    pantalla = PantallaInicio()
    qtbot.addWidget(pantalla)
    nuevos, otros = [], []
    pantalla.nuevo_pedido.connect(lambda: nuevos.append(1))
    pantalla.abrir_otro_pedido.connect(lambda: otros.append(1))

    pantalla.boton_nuevo.click()
    pantalla.boton_abrir_otro.click()

    assert nuevos == [1] and otros == [1]


def test_sin_recientes_invita_a_empezar(qtbot):
    pantalla = PantallaInicio()
    qtbot.addWidget(pantalla)
    pantalla.set_recientes([])

    assert pantalla.nombres_visibles() == []
    assert not pantalla.boton_nuevo.isHidden()
    assert not pantalla.vacio.isHidden()


def test_con_recientes_el_cartel_de_vacio_se_va(qtbot):
    """Los dos a la vez serian contradictorios: una lista con proyectos y un
    cartel diciendo que no hay ninguno."""
    pantalla = PantallaInicio()
    qtbot.addWidget(pantalla)
    pantalla.set_recientes([Reciente(Path("/a/uno.cvproj"), "Uno", "")])

    assert pantalla.vacio.isHidden()


def test_volver_a_llenar_la_lista_no_deja_las_filas_viejas(qtbot):
    """`set_recientes` se llama cada vez que se vuelve a esta pantalla. Si
    las filas anteriores siguieran vivas, la lista crece sola."""
    pantalla = PantallaInicio()
    qtbot.addWidget(pantalla)
    pantalla.set_recientes([Reciente(Path("/a/uno.cvproj"), "Uno", "")])
    pantalla.set_recientes([Reciente(Path("/a/dos.cvproj"), "Dos", "")])

    assert pantalla.nombres_visibles() == ["Dos"]
    assert len(pantalla.lista_host.findChildren(type(pantalla.filas[0]))) == 1


def test_se_puede_quitar_de_la_lista(qtbot, tmp_path):
    """Un proyecto que ya no existe se quita a mano: podarlo solo seria
    borrarle a Bruno la prueba de que estuvo ahi."""
    pantalla = PantallaInicio()
    qtbot.addWidget(pantalla)
    ruta = tmp_path / "no-esta.cvproj"
    pantalla.set_recientes([Reciente(ruta, "Fantasma", "")])
    quitados = []
    pantalla.quitar_pedido.connect(quitados.append)

    menu = pantalla.filas[0].menu_de_contexto()
    menu.actions()[0].trigger()

    assert quitados == [ruta]


def test_dos_rutas_con_el_mismo_prefijo_no_se_leen_iguales(qtbot):
    """La carpeta del proyecto va al FINAL de la ruta, y es lo unico que
    distingue una fila de otra cuando los dos cuelgan de la misma raiz.
    Cortando por el final se pierde justo eso y las dos filas se leen
    identicas -- por eso se elide por el medio, como el nombre de archivo
    sobre el video."""
    raiz = "/Volumes/SSD_RODAJE_2026/Clientes/Inmuebles/Entregas del año 2026"
    pantalla = PantallaInicio()
    qtbot.addWidget(pantalla)
    pantalla.set_recientes([
        Reciente(Path(f"{raiz}/IAV-2608.04-A/A.cvproj"), "Torre A", "2026-08-09 10:00"),
        Reciente(Path(f"{raiz}/IAV-2608.04-B/B.cvproj"), "Torre B", "2026-08-08 09:00"),
    ])
    pantalla.resize(420, 320)
    pantalla.grab()   # obliga a Qt a acomodar el layout antes de medir

    uno, dos = (f.detalle.text() for f in pantalla.filas)
    assert uno != dos, "las dos filas se leen igual: la carpeta se perdio al elidir"
    assert uno.endswith("IAV-2608.04-A")
    assert dos.endswith("IAV-2608.04-B")


def test_el_tooltip_trae_la_ruta_entera_sin_cortar(qtbot):
    """La elidida es para el vistazo; la completa se lee aqui."""
    larga = Path("/Volumes/" + "/".join(["CARPETA_CON_NOMBRE_LARGUISIMO"] * 6) + "/P.cvproj")
    pantalla = PantallaInicio()
    qtbot.addWidget(pantalla)
    pantalla.set_recientes([Reciente(larga, "Proyecto", "2026-08-09 10:00")])
    pantalla.resize(420, 320)
    pantalla.grab()

    assert pantalla.filas[0].toolTip() == str(larga)
    assert "…" not in pantalla.filas[0].toolTip()


def test_una_ruta_larga_no_empuja_el_ancho(qtbot):
    """Una carpeta con nombre largo no puede decidir el ancho de la ventana:
    se corta con puntos suspensivos, como en el rail de cuartos."""
    larga = Path("/Volumes/" + "/".join(["CARPETA_CON_NOMBRE_LARGUISIMO"] * 6) + "/P.cvproj")
    pantalla = PantallaInicio()
    qtbot.addWidget(pantalla)
    pantalla.set_recientes([Reciente(larga, "Proyecto", "2026-08-09 10:00")])
    pantalla.resize(420, 320)
    pantalla.grab()   # obliga a Qt a acomodar el layout antes de medir

    detalle = pantalla.filas[0].detalle
    assert detalle.text() != detalle.full_text()
    assert pantalla.minimumSizeHint().width() < 420
