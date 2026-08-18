# tests/ui/test_pantalla_inicio.py
from pathlib import Path

from PySide6.QtWidgets import QMenu

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
    existio y que el disco no esta conectado, no que desaparecio.

    Se comprueba lo que PASA --se ve apagado y no abre-- y no `isEnabled()`,
    que era el mecanismo: apagar el widget tambien le quitaba el clic
    derecho, o sea el unico «Quitar de la lista» que tiene la pantalla. El
    test amarrado al mecanismo habria dado verde con ese bug puesto.
    """
    pantalla = PantallaInicio()
    qtbot.addWidget(pantalla)
    pantalla.set_recientes([Reciente(tmp_path / "no-esta.cvproj", "Fantasma", "")])
    abiertos = []
    pantalla.abrir_pedido.connect(abiertos.append)

    fila = pantalla.filas[0]
    assert fila.property("perdido") == "true"
    assert fila.nombre.property("apagado") == "true"
    assert "No se encuentra" in fila.detalle.full_text()
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


# --- el aviso, en la pantalla y no en un modal ------------------------------


def test_sin_nada_que_decir_no_hay_aviso(qtbot):
    pantalla = PantallaInicio()
    qtbot.addWidget(pantalla)

    assert pantalla.aviso.isHidden()


def test_el_aviso_se_muestra_en_la_pantalla(qtbot):
    """Un renglón en la propia pantalla, no un `QMessageBox`: los modales
    bloquean con `exec` por dentro —tanto que la suite tiene que parchearlos
    para no colgarse— y el spec de esta fase los descarta fuera de los
    selectores de archivo del sistema."""
    pantalla = PantallaInicio()
    qtbot.addWidget(pantalla)
    pantalla.show()

    pantalla.avisar("No se pudo abrir «Casa Lomas.cvproj».")

    assert pantalla.aviso.isVisible()
    assert "Casa Lomas" in pantalla.aviso.text()


def test_el_aviso_se_va_al_intentar_otra_cosa(qtbot):
    """Si se quedara puesto, el error de hace tres clics seguiría ahí
    contradiciendo lo que acaba de pasar."""
    pantalla = PantallaInicio()
    qtbot.addWidget(pantalla)
    pantalla.show()
    pantalla.avisar("algo salió mal")

    pantalla.callar()

    assert pantalla.aviso.isHidden()


def test_la_pantalla_no_abre_ningun_modal(qtbot):
    """Guardarraíl del acuerdo, no del código de hoy.

    Se mira lo que el módulo IMPORTA y lo que LLAMA, no el texto suelto: los
    comentarios de aquí nombran a `QMessageBox` justo para explicar por qué
    no se usa, y un test que grepea el archivo entero se caería con ellos.
    """
    import ast
    import inspect

    from clasificador_video.ui import pantalla_inicio

    arbol = ast.parse(inspect.getsource(pantalla_inicio))
    importado = {
        alias.name for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.ImportFrom) for alias in nodo.names
    }
    llamado = {
        nodo.func.attr for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute)
    }
    assert "QMessageBox" not in importado
    assert "exec" not in llamado


# --- el proyecto que ya no esta se puede quitar ---------------------------


def _fila_perdida(qtbot, tmp_path):
    pantalla = PantallaInicio()
    qtbot.addWidget(pantalla)
    pantalla.set_recientes([
        Reciente(tmp_path / "no-esta.cvproj", "Perdido", "2026-08-01 10:00"),
    ])
    return pantalla, pantalla.filas[0]


def test_el_renglon_de_un_proyecto_perdido_recibe_el_clic_derecho(qtbot, tmp_path):
    """Un widget apagado con `setEnabled(False)` NO recibe eventos de mouse,
    y eso incluye el clic derecho: Qt los descarta antes de entregarlos. Con
    la fila apagada, el unico «Quitar de la lista» que tiene la pantalla
    quedaba fuera de alcance -- justo en los renglones que uno quiere quitar,
    que son los que ya no estan.
    """
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QContextMenuEvent
    from PySide6.QtWidgets import QApplication

    pantalla, fila = _fila_perdida(qtbot, tmp_path)
    assert fila.disponible is False

    llamadas = []
    fila.menu_de_contexto = lambda: llamadas.append(1) or QMenu()
    evento = QContextMenuEvent(QContextMenuEvent.Reason.Mouse, QPoint(10, 10),
                               fila.mapToGlobal(QPoint(10, 10)))
    QApplication.instance().notify(fila, evento)

    assert llamadas == [1]


def test_quitar_de_la_lista_un_proyecto_perdido_llega_a_la_pantalla(qtbot, tmp_path):
    pantalla, fila = _fila_perdida(qtbot, tmp_path)
    quitados = []
    pantalla.quitar_pedido.connect(quitados.append)

    fila.menu_de_contexto().actions()[0].trigger()

    assert quitados == [tmp_path / "no-esta.cvproj"]


def test_clickear_un_proyecto_perdido_no_lo_intenta_abrir(qtbot, tmp_path):
    """Se ve gris y no se abre. Lo que cambio es COMO se apaga, no que se
    pueda abrir: prometerlo seria peor que verlo gris."""
    pantalla, fila = _fila_perdida(qtbot, tmp_path)
    intentos = []
    pantalla.abrir_pedido.connect(intentos.append)

    fila.click()

    assert intentos == []


def test_clickear_uno_que_si_esta_lo_abre(qtbot, tmp_path):
    proyecto = tmp_path / "vivo.cvproj"
    proyecto.write_text("{}")
    pantalla = PantallaInicio()
    qtbot.addWidget(pantalla)
    pantalla.set_recientes([Reciente(proyecto, "Vivo", "2026-08-02 10:00")])
    abiertos = []
    pantalla.abrir_pedido.connect(abiertos.append)

    pantalla.filas[0].click()

    assert abiertos == [proyecto]
