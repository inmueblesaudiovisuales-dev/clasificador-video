# tests/ui/test_room_palette.py
from PySide6.QtCore import Qt

from clasificador_video.ui import theme
from clasificador_video.ui.room_palette import RoomPalette


def _paleta(qtbot, cuartos, conteos=None, seleccionados=1) -> RoomPalette:
    paleta = RoomPalette()
    qtbot.addWidget(paleta)
    paleta.abrir(cuartos, conteos or {}, seleccionados)
    return paleta


def test_sin_escribir_nada_muestra_todos_los_cuartos(qtbot):
    """Se abre para ELEGIR, no solo para buscar: con la lista a la vista, `⏎`
    y una flecha bastan cuando el cuarto no tiene tecla."""
    paleta = _paleta(qtbot, ["Cocina", "Sala"])
    assert paleta.opciones_visibles() == ["Cocina", "Sala"]


def test_filtra_los_cuartos_en_vivo(qtbot):
    paleta = _paleta(qtbot, ["Cocina", "Recámara 1", "Recámara 2"])
    paleta.input.setText("reca")
    assert paleta.opciones_visibles() == ["Recámara 1", "Recámara 2"]


def test_la_busqueda_ignora_acentos(qtbot):
    """En un teclado apurado nadie escribe los acentos."""
    paleta = _paleta(qtbot, ["Recámara 1"])
    paleta.input.setText("recamara")
    assert paleta.opciones_visibles() == ["Recámara 1"]


def test_la_busqueda_ignora_mayusculas(qtbot):
    paleta = _paleta(qtbot, ["Cocina"])
    paleta.input.setText("COCI")
    assert paleta.opciones_visibles() == ["Cocina"]


def test_enter_asigna_la_primera_opcion(qtbot):
    paleta = _paleta(qtbot, ["Cocina", "Comedor"])
    paleta.input.setText("com")
    with qtbot.waitSignal(paleta.room_chosen) as blocker:
        paleta.confirmar()
    assert blocker.args == ["Comedor"]


def test_al_confirmar_se_cierra(qtbot):
    paleta = _paleta(qtbot, ["Cocina"])
    paleta.confirmar()
    assert paleta.isHidden()


def test_sin_coincidencias_ofrece_crear(qtbot):
    paleta = _paleta(qtbot, ["Cocina"])
    paleta.input.setText("Alberca")
    assert paleta.opcion_de_crear() == "Alberca"
    with qtbot.waitSignal(paleta.room_created) as blocker:
        paleta.confirmar()
    assert blocker.args == ["Alberca"]


def test_con_el_campo_vacio_no_ofrece_crear_nada(qtbot):
    paleta = _paleta(qtbot, ["Cocina"])
    assert paleta.opcion_de_crear() is None


def test_un_nombre_que_ya_existe_no_se_ofrece_crear(qtbot):
    """Crear un segundo «Cocina» partiria el cuarto en dos con el mismo
    nombre, y el rail mostraria dos filas iguales."""
    paleta = _paleta(qtbot, ["Cocina"])
    paleta.input.setText("Cocina")
    assert paleta.opcion_de_crear() is None


def test_escribir_algo_parecido_igual_deja_crear(qtbot):
    """`rec` coincide con Recámara 1 y 2, pero puede que quieras un cuarto
    NUEVO que se llame asi: la opcion de crear convive con las coincidencias
    (el mockup las muestra juntas)."""
    paleta = _paleta(qtbot, ["Recámara 1", "Recámara 2"])
    paleta.input.setText("rec")
    assert paleta.opciones_visibles() == ["Recámara 1", "Recámara 2"]
    assert paleta.opcion_de_crear() == "rec"


def test_las_flechas_mueven_la_seleccion(qtbot):
    paleta = _paleta(qtbot, ["Cocina", "Comedor"])
    qtbot.keyClick(paleta.input, Qt.Key.Key_Down)
    assert paleta.opcion_activa() == "Comedor"


def test_la_flecha_no_se_pasa_del_final(qtbot):
    paleta = _paleta(qtbot, ["Cocina", "Comedor"])
    for _ in range(5):
        qtbot.keyClick(paleta.input, Qt.Key.Key_Down)
    assert paleta.opcion_activa() == "Comedor"


def test_al_escribir_la_seleccion_vuelve_a_la_primera(qtbot):
    """Si se quedara en la fila 2 mientras la lista cambia debajo, `⏎`
    asignaria un cuarto que ya no es el que estas viendo arriba."""
    paleta = _paleta(qtbot, ["Cocina", "Comedor", "Sala"])
    qtbot.keyClick(paleta.input, Qt.Key.Key_Down)
    paleta.input.setText("co")
    assert paleta.opcion_activa() == "Cocina"


def test_esc_cierra_sin_asignar(qtbot):
    paleta = _paleta(qtbot, ["Cocina"])
    with qtbot.assertNotEmitted(paleta.room_chosen):
        qtbot.keyClick(paleta.input, Qt.Key.Key_Escape)
    assert paleta.isHidden()


def test_dice_a_cuantos_clips_va_a_aplicar(qtbot):
    """El mockup dice `a 5 clips`: asignar en lote sin querer es el error mas
    caro de la app."""
    paleta = _paleta(qtbot, ["Cocina"], seleccionados=6)
    assert "6 clips" in paleta.alcance_label.text()


def test_con_un_solo_clip_no_dice_a_1_clips(qtbot):
    paleta = _paleta(qtbot, ["Cocina"], seleccionados=1)
    assert "1 clips" not in paleta.alcance_label.text()


def test_cada_opcion_lleva_su_tecla_y_su_color(qtbot):
    """Las mismas señas que el rail: la paleta no es otra lista de cuartos,
    es la misma vista de otra forma."""
    paleta = _paleta(qtbot, ["Cocina", "Sala"], conteos={"Cocina": 24})
    primera = paleta.filas_visibles()[0]
    assert primera.key_cap.text() == "1"
    assert theme.room_color(0) in primera.swatch.styleSheet()
    assert primera.count_label.text() == "24"


def test_los_cuartos_sin_tecla_no_inventan_una(qtbot):
    """A partir del decimo no hay atajo numerico: el hueco queda vacio en vez
    de mentir con un numero que no funciona. Y son justamente los cuartos por
    los que esta paleta existe."""
    cuartos = [f"Cuarto {i:02d}" for i in range(12)]
    paleta = _paleta(qtbot, cuartos)
    # se busca el decimo: la paleta muestra pocas filas a la vez, asi que sin
    # buscarlo ni siquiera aparece -- y ese es justamente el caso de uso
    paleta.input.setText("Cuarto 09")
    assert paleta.opciones_visibles() == ["Cuarto 09"]
    assert paleta.filas_visibles()[0].key_cap.text() == ""

    paleta.input.setText("Cuarto 08")            # el noveno SI tiene tecla
    assert paleta.filas_visibles()[0].key_cap.text() == "9"


def test_el_pie_dice_las_tres_teclas(qtbot):
    paleta = _paleta(qtbot, ["Cocina"])
    pie = paleta.foot_label.text()
    for tecla in ("↑", "↓", "⏎", "esc"):
        assert tecla in pie
