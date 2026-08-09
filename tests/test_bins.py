from pathlib import Path

from clasificador_video.bins import BinTree


def test_un_bin_nuevo_queda_al_final_con_sus_clips():
    arbol = BinTree()
    arbol.agregar("Sony FX30", Path("/cam"), [0, 1, 2])
    arbol.agregar("Dron", Path("/dron"), [3, 4])

    assert arbol.nombres() == ["Sony FX30", "Dron"]
    assert arbol.clips_de("Dron") == [3, 4]


def test_el_bin_de_un_clip():
    arbol = BinTree()
    arbol.agregar("Sony FX30", Path("/cam"), [0, 1])
    arbol.agregar("Dron", Path("/dron"), [2])

    assert arbol.bin_de(1) == "Sony FX30"
    assert arbol.bin_de(2) == "Dron"
    assert arbol.bin_de(99) is None


def test_dos_bins_no_pueden_llamarse_igual():
    """Dos con el mismo nombre serian dos encabezados identicos en la hoja
    y un menu de clic derecho que no se sabe a cual aplica."""
    arbol = BinTree()
    arbol.agregar("Dron", Path("/a"), [0])
    arbol.agregar("Dron", Path("/b"), [1])

    assert arbol.nombres() == ["Dron", "Dron 2"]


def test_renombrar_conserva_la_posicion():
    """La posicion es el orden en la hoja: renombrar no puede moverlo."""
    arbol = BinTree()
    arbol.agregar("Sony FX30", Path("/cam"), [0])
    arbol.agregar("Dron", Path("/dron"), [1])

    arbol.renombrar("Sony FX30", "Sony A")

    assert arbol.nombres() == ["Sony A", "Dron"]
    assert arbol.clips_de("Sony A") == [0]


def test_renombrar_a_uno_que_ya_existe_no_hace_nada():
    arbol = BinTree()
    arbol.agregar("Dron", Path("/a"), [0])
    arbol.agregar("Sony", Path("/b"), [1])

    arbol.renombrar("Sony", "Dron")

    assert arbol.nombres() == ["Dron", "Sony"]


def test_sumar_clips_a_un_bin_que_ya_existe():
    arbol = BinTree()
    arbol.agregar("Dron", Path("/dron"), [0, 1])

    arbol.sumar("Dron", [2, 3])

    assert arbol.clips_de("Dron") == [0, 1, 2, 3]


def test_quitar_un_bin_devuelve_los_indices_que_se_van():
    """Quien llama tiene que borrar esos clips de la lista y de todo lo que
    va indexado por clip. Si no los devolviera, habria que adivinarlos."""
    arbol = BinTree()
    arbol.agregar("Dron", Path("/dron"), [0, 1])
    arbol.agregar("Sony", Path("/cam"), [2])

    assert arbol.quitar("Dron") == [0, 1]
    assert arbol.nombres() == ["Sony"]


def test_reindexar_despues_de_quitar_clips():
    """Al borrar los clips 0 y 1, el que era 2 pasa a ser 0. Los bins van
    por INDICE, asi que si no se recorren quedan apuntando a otro clip."""
    arbol = BinTree()
    arbol.agregar("Dron", Path("/dron"), [0, 1])
    arbol.agregar("Sony", Path("/cam"), [2, 3])

    arbol.reindexar_tras_quitar([0, 1])

    assert arbol.clips_de("Sony") == [0, 1]


def test_ida_y_vuelta_a_json():
    arbol = BinTree()
    arbol.agregar("Dron", Path("/dron"), [0, 1])
    arbol.agregar("Sony", Path("/cam"), [2])

    otro = BinTree.from_list(arbol.to_list())

    assert otro.nombres() == ["Dron", "Sony"]
    assert otro.clips_de("Dron") == [0, 1]
    assert otro.clips_de("Sony") == [2]


def test_una_sesion_vieja_sin_bins_cae_en_uno_solo():
    """Nadie pierde una sesion por actualizar la app. Sin la llave `bins`,
    todo el material queda en un bin unico con la carpeta del primer clip.
    """
    arbol = BinTree.desde_sesion(
        None, rutas=[Path("/material/A.MP4"), Path("/material/B.MP4")]
    )

    assert arbol.nombres() == ["material"]
    assert arbol.clips_de("material") == [0, 1]


def test_una_sesion_vieja_sin_clips_no_inventa_un_bin():
    assert BinTree.desde_sesion(None, rutas=[]).nombres() == []


def test_desde_sesion_descarta_indices_fuera_de_rango():
    """Una sesion corrupta o de un proyecto con menos clips que antes no
    puede dejar un bin apuntando a un indice que no existe -- eso es
    exactamente el IndexError que revienta el menu de un bin en la F3."""
    datos = [{"nombre": "Sony", "origen": "/cam", "clips": [-1, 0, 1, 5]}]

    arbol = BinTree.desde_sesion(datos, rutas=[Path("/cam/A.MP4"), Path("/cam/B.MP4")])

    assert arbol.clips_de("Sony") == [0, 1]


def test_desde_sesion_deja_sueltos_a_los_huerfanos():
    """Un clip suelto se representa por AUSENCIA, no por un bin llamado
    «Sin bin».

    Antes se les inventaba un bin real con ese nombre. Dos problemas: la
    hoja usa esa misma cadena como titulo de la seccion de sueltos, asi
    que el encabezado saldria dos veces reusando el mismo widget en dos
    posiciones del layout; y convertia el estado «clip suelto» --que la
    §6.b del spec declara valido-- en un bin normal al reabrir.
    """
    datos = [{"nombre": "Sony", "origen": "/cam", "clips": [0]}]

    arbol = BinTree.desde_sesion(
        datos, rutas=[Path("/cam/A.MP4"), Path("/dron/D.MP4"), Path("/dron/E.MP4")]
    )

    assert arbol.clips_de("Sony") == [0]
    assert arbol.nombres() == ["Sony"]
    assert [arbol.bin_de(i) for i in (1, 2)] == [None, None]


def test_bins_vacios_a_proposito_no_inventan_uno_con_las_rutas():
    """`[]` es distinto de `None`: es que el usuario se quedo sin bins a
    proposito (por ejemplo, borro el ultimo). Tratarlo como "sesion vieja"
    resucitaria lo que acaba de borrar."""
    arbol = BinTree.desde_sesion([], rutas=[])

    assert arbol.nombres() == []


def test_from_list_con_basura_no_revienta():
    """`load_session` en autosave.py ya se blinda contra JSON malformado;
    `from_list` sigue la misma simetria -- lo que no se entiende se
    descarta, no revienta `_restore_session` y deja la app sin poder
    abrir."""
    assert BinTree.from_list("esto no es una lista").nombres() == []
    assert BinTree.from_list(["tampoco esto es un bin"]).nombres() == []
    assert BinTree.from_list([{"nombre": "Dron", "origen": "/d", "clips": ["a"]}]).nombres() == []


def test_el_mapa_de_bin_por_clip():
    """Lo que necesita el filtro: preguntarle a `bin_de` por cada clip
    recorreria todos los bins una vez por clip."""
    arbol = BinTree()
    arbol.agregar("Sony", Path("/cam"), [0, 2])
    arbol.agregar("Dron", Path("/dron"), [1])

    assert arbol.mapa_por_clip() == {0: "Sony", 2: "Sony", 1: "Dron"}


def test_un_bin_vacio_existe_y_se_queda():
    """Si un bin sin clips desapareciera, no se podria crear primero y
    llenar despues -- que es justo el gesto que se esta agregando."""
    arbol = BinTree()
    arbol.crear_vacio("Dron")

    assert arbol.nombres() == ["Dron"]
    assert arbol.clips_de("Dron") == []


def test_crear_vacio_no_repite_nombres():
    arbol = BinTree()
    arbol.crear_vacio("Dron")

    assert arbol.crear_vacio("Dron") == "Dron 2"


def test_mover_saca_del_bin_viejo_y_mete_en_el_nuevo():
    arbol = BinTree()
    arbol.agregar("Sony", Path("/cam"), [0, 1, 2])
    arbol.crear_vacio("Dron")

    arbol.mover([0, 2], "Dron")

    assert arbol.clips_de("Sony") == [1]
    assert arbol.clips_de("Dron") == [0, 2]


def test_mover_a_ningun_bin_los_deja_sueltos():
    """`None` es «sacalo de donde este»: los clips sueltos son un estado
    valido, no un error. Van a la seccion «Sin bin»."""
    arbol = BinTree()
    arbol.agregar("Sony", Path("/cam"), [0, 1])

    arbol.mover([0], None)

    assert arbol.clips_de("Sony") == [1]
    assert arbol.bin_de(0) is None


def test_mover_a_su_propio_bin_no_hace_nada():
    arbol = BinTree()
    arbol.agregar("Sony", Path("/cam"), [0, 1])

    arbol.mover([0], "Sony")

    assert arbol.clips_de("Sony") == [0, 1]


def test_mover_conserva_el_orden_de_llegada():
    """El orden dentro del bin es el orden de rodaje, no el de arrastre:
    de el vive la nocion de «el clip anterior»."""
    arbol = BinTree()
    arbol.agregar("Sony", Path("/cam"), [5])
    arbol.crear_vacio("Dron")

    arbol.mover([3, 1], "Dron")

    assert arbol.clips_de("Dron") == [1, 3]
