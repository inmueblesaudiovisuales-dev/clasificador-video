import logging
from pathlib import Path

from clasificador_video.revinculo import (
    buscar_bajo,
    calza,
    cuadros_esperados_de,
    faltantes_de,
    reencontrar_bin,
)


def test_NO_calza_un_tocayo_de_otro_tamano(tmp_path):
    """EL test de este plan. Un archivo con el nombre correcto y el
    contenido equivocado no se engancha. Es el caso de dos tarjetas de la
    misma camara, que numeran igual desde cero.
    """
    archivo = tmp_path / "C0001.MP4"
    archivo.write_bytes(b"x" * 999)

    assert calza(archivo, tamano_esperado=500, cuadros_esperados=300,
                 medir=lambda p: {"duration_frames": 300}) is False


def test_sin_ningun_dato_con_que_comparar_NO_confirma(tmp_path):
    """«Confirmado por falta de evidencia» es exactamente al reves de lo que
    este modulo promete. Un proyecto sin peso ni duracion guardados para ese
    clip no puede decir que el archivo sea el que era."""
    archivo = tmp_path / "C0001.MP4"
    archivo.write_bytes(b"x" * 500)

    assert calza(archivo, tamano_esperado=None, cuadros_esperados=None,
                 medir=lambda p: {"duration_frames": 300}) is False


def test_un_archivo_que_no_existe_no_calza(tmp_path):
    """Sin peso guardado no se llegaba a tocar el disco, y un archivo que ni
    siquiera esta ahi salia «confirmado»."""
    assert calza(tmp_path / "no-esta.MP4", tamano_esperado=None,
                 cuadros_esperados=300,
                 medir=lambda p: {"duration_frames": 300}) is False


def test_si_medir_no_trae_la_duracion_no_calza(tmp_path):
    """«No se pudo medir» y «dura cero cuadros» son cosas distintas, y
    colapsarlas en el numero 0 hacia que un clip de cero o un cuadro lo
    confirmara cualquier archivo ilegible."""
    archivo = tmp_path / "C0001.MP4"
    archivo.write_bytes(b"x" * 500)

    assert calza(archivo, tamano_esperado=500, cuadros_esperados=0,
                 medir=lambda p: {}) is False
    assert calza(archivo, tamano_esperado=500, cuadros_esperados=0,
                 medir=lambda p: None) is False


def test_un_error_de_cableado_deja_rastro(tmp_path, caplog):
    """Un `medir` mal conectado se veia igual que un archivo roto: nada se
    reconecta y ni una pista de por que. El archivo ilegible es esperado y
    va callado; el error de programacion no."""
    archivo = tmp_path / "C0001.MP4"
    archivo.write_bytes(b"x" * 500)

    with caplog.at_level(logging.WARNING):
        assert calza(archivo, tamano_esperado=500, cuadros_esperados=300,
                     medir=lambda p, y: None) is False

    assert caplog.records


def test_calza_cuando_coinciden_tamano_y_cuadros(tmp_path):
    archivo = tmp_path / "C0001.MP4"
    archivo.write_bytes(b"x" * 500)

    assert calza(archivo, tamano_esperado=500, cuadros_esperados=300,
                 medir=lambda p: {"duration_frames": 300}) is True


def test_NO_calza_si_dura_distinto(tmp_path):
    archivo = tmp_path / "C0001.MP4"
    archivo.write_bytes(b"x" * 500)

    assert calza(archivo, tamano_esperado=500, cuadros_esperados=300,
                 medir=lambda p: {"duration_frames": 450}) is False


def test_un_cuadro_de_diferencia_se_tolera(tmp_path):
    """Mismo margen que `_el_proxy_calza`: ffprobe redondea distinto segun
    el contenedor, y un cuadro no distingue dos tomas."""
    archivo = tmp_path / "C0001.MP4"
    archivo.write_bytes(b"x" * 500)

    assert calza(archivo, tamano_esperado=500, cuadros_esperados=301,
                 medir=lambda p: {"duration_frames": 300}) is True


def test_sin_datos_guardados_basta_el_tamano(tmp_path):
    """Una sesion vieja puede no traer la duracion de todos los clips. Sin
    ese dato se confirma solo con el tamaño, que ya descarta al tocayo, en
    vez de rechazar material bueno."""
    archivo = tmp_path / "C0001.MP4"
    archivo.write_bytes(b"x" * 500)

    assert calza(archivo, tamano_esperado=500, cuadros_esperados=None,
                 medir=lambda p: {"duration_frames": 300}) is True


def test_si_no_se_puede_medir_no_calza(tmp_path):
    """Un archivo que ffprobe no puede leer no es «el que era»: es un
    archivo roto con el nombre correcto."""
    archivo = tmp_path / "C0001.MP4"
    archivo.write_bytes(b"x" * 500)

    def revienta(p):
        raise OSError("no se pudo leer")

    assert calza(archivo, tamano_esperado=500, cuadros_esperados=300,
                 medir=revienta) is False


def test_encuentra_por_la_ruta_relativa_exacta(tmp_path):
    (tmp_path / "sub").mkdir()
    esperado = tmp_path / "sub" / "C0001.MP4"
    esperado.write_bytes(b"x")

    assert buscar_bajo(tmp_path, "sub/C0001.MP4") == esperado


def test_si_no_esta_en_su_sitio_lo_busca_por_nombre(tmp_path):
    """La carpeta pudo reorganizarse. Buscar por nombre es el plan B, y por
    eso lo que se encuentre asi tiene que CONFIRMARSE (ver `calza`)."""
    (tmp_path / "otra").mkdir()
    esta = tmp_path / "otra" / "C0001.MP4"
    esta.write_bytes(b"x")

    assert buscar_bajo(tmp_path, "sub/C0001.MP4") == esta


def test_con_dos_tocayos_no_elige_ninguno(tmp_path):
    """Las camaras renumeran desde cero en cada tarjeta: dos `C0001.MP4`
    bajo la misma carpeta es un caso REAL, no rebuscado. Elegir uno al azar
    seria enganchar material equivocado sin que nadie se entere."""
    for sub in ("tarjeta1", "tarjeta2"):
        (tmp_path / sub).mkdir()
        (tmp_path / sub / "C0001.MP4").write_bytes(b"x")

    assert buscar_bajo(tmp_path, "no-esta/C0001.MP4") is None


def test_si_esta_en_su_sitio_los_tocayos_no_estorban(tmp_path):
    """La ruta relativa desempata: si el archivo esta donde decia, se toma
    ese y los tocayos de otras carpetas dan igual."""
    for sub in ("sub", "tarjeta2"):
        (tmp_path / sub).mkdir()
        (tmp_path / sub / "C0001.MP4").write_bytes(b"x")

    assert buscar_bajo(tmp_path, "sub/C0001.MP4") == tmp_path / "sub" / "C0001.MP4"


def test_una_carpeta_que_no_existe_no_revienta(tmp_path):
    assert buscar_bajo(tmp_path / "no-esta", "C0001.MP4") is None


def test_faltantes_de_lista_lo_que_no_esta(tmp_path):
    """Recibe y devuelve INDICES DE CLIP, como todo el resto del modulo. Con
    una lista devolvia posiciones, que en un bin cualquiera no son los
    mismos numeros -- y confundirlos reconecta el clip equivocado."""
    esta = tmp_path / "A.MP4"
    esta.write_bytes(b"x")

    assert faltantes_de({7: esta, 9: tmp_path / "B.MP4"}) == [9]


def test_reencontrar_devuelve_los_que_calzan_y_los_que_no(tmp_path):
    nueva = tmp_path / "nueva"
    nueva.mkdir()
    bueno = nueva / "C0001.MP4"
    bueno.write_bytes(b"x" * 500)
    tocayo = nueva / "C0002.MP4"
    tocayo.write_bytes(b"x" * 111)          # peso equivocado: no calza

    resultado = reencontrar_bin(
        carpeta=nueva,
        relativas={0: "C0001.MP4", 1: "C0002.MP4"},
        bytes_esperados={0: 500, 1: 999},
        cuadros_esperados={},
        medir=lambda p: {"duration_frames": 0},
    )

    assert resultado.reconectados == {0: bueno}
    assert resultado.sin_confirmar == [1]


def test_lo_que_no_aparece_queda_como_no_encontrado(tmp_path):
    nueva = tmp_path / "nueva"
    nueva.mkdir()

    resultado = reencontrar_bin(
        carpeta=nueva, relativas={0: "C0001.MP4"},
        bytes_esperados={0: 500}, cuadros_esperados={},
        medir=lambda p: {"duration_frames": 0},
    )

    assert resultado.reconectados == {}
    assert resultado.no_encontrados == [0]


def test_un_nombre_con_corchetes_no_se_usa_como_patron(tmp_path):
    """`rglob` trataba el nombre como patron, asi que `C0001[1].MP4`
    matcheaba con `C00011.MP4` -- otro archivo, con otro material. No basta
    con que a veces falle del lado seguro: aqui sobre-encontraba."""
    (tmp_path / "otra").mkdir()
    (tmp_path / "otra" / "C00011.MP4").write_bytes(b"x")

    assert buscar_bajo(tmp_path, "sub/C0001[1].MP4") is None


def test_un_nombre_con_corchetes_si_se_encuentra_a_si_mismo(tmp_path):
    """Y del otro lado: el archivo de verdad tiene que aparecer. Las copias
    duplicadas se llaman asi todo el tiempo."""
    (tmp_path / "otra").mkdir()
    real = tmp_path / "otra" / "C0001[1].MP4"
    real.write_bytes(b"x")

    assert buscar_bajo(tmp_path, "sub/C0001[1].MP4") == real


def test_un_asterisco_en_el_nombre_no_matchea_cualquier_cosa(tmp_path):
    """`*` y `?` son legales en un nombre de archivo en macOS."""
    (tmp_path / "otra").mkdir()
    (tmp_path / "otra" / "C0001.MP4").write_bytes(b"x")

    assert buscar_bajo(tmp_path, "sub/*.MP4") is None


def test_no_se_sale_de_la_carpeta_que_Bruno_señalo(tmp_path):
    """El `.cvproj` es dato externo: pudo escribirlo una version anterior al
    filtro de `..`, o editarse a mano. Que la relativa se haya validado al
    ESCRIBIR no sirve de nada aqui, donde se lee."""
    carpeta = tmp_path / "nueva"
    carpeta.mkdir()
    fuera = tmp_path / "fuera.MP4"
    fuera.write_bytes(b"x")

    assert buscar_bajo(carpeta, "../fuera.MP4") is None
    assert buscar_bajo(carpeta, str(fuera)) is None


def test_una_relativa_vacia_no_revienta(tmp_path):
    """Tronaba con un ValueError sin atrapar, en pleno abrir proyecto."""
    assert buscar_bajo(tmp_path, "") is None


def test_el_fallback_por_nombre_ignora_mayusculas(tmp_path):
    """La busqueda literal ya era insensible en APFS, asi que un `c0001.mp4`
    se encontraba por un camino y no por el otro. Que dependa de cual de los
    dos caminos tomo es justo lo que no se quiere."""
    (tmp_path / "otra").mkdir()
    real = tmp_path / "otra" / "c0001.mp4"
    real.write_bytes(b"x")

    assert buscar_bajo(tmp_path, "sub/C0001.MP4") == real


def test_dos_clips_no_pueden_quedar_enganchados_al_mismo_archivo(tmp_path):
    """Dos tarjetas de la Sony, cada una con su `C0001.MP4`, y en la carpeta
    nueva sobrevivio una sola copia: el fallback por nombre la devolvia para
    los DOS. Bruno terminaba con dos clips que son el mismo video, con
    marcas distintas cada uno, y nada que se lo dijera."""
    nueva = tmp_path / "nueva"
    (nueva / "sobreviviente").mkdir(parents=True)
    unico = nueva / "sobreviviente" / "C0001.MP4"
    unico.write_bytes(b"x" * 500)

    resultado = reencontrar_bin(
        carpeta=nueva,
        relativas={0: "tarjeta1/C0001.MP4", 1: "tarjeta2/C0001.MP4"},
        bytes_esperados={0: 500, 1: 500},
        cuadros_esperados={},
        medir=lambda p: {"duration_frames": 0},
    )

    assert resultado.reconectados == {}
    # DISPUTADOS, no «sin confirmar»: el archivo si calzaba con los dos. El
    # problema no es que no sea el mismo video --lo es-- sino que no puede
    # ser dos clips a la vez. Decirlo como «no es el mismo» seria afirmar
    # algo que no se comprobo.
    assert resultado.disputados == [0, 1]
    assert resultado.sin_confirmar == []


def test_sin_datos_para_confirmar_no_es_lo_mismo_que_no_aparecio(tmp_path):
    """El archivo esta ahi; lo que falta es con que comprobar que sea el
    mismo. A Bruno hay que decirle eso, no «no aparecio» ni «no es el
    mismo»: nadie comprobo nada."""
    nueva = tmp_path / "nueva"
    nueva.mkdir()
    (nueva / "C0001.MP4").write_bytes(b"x" * 500)

    resultado = reencontrar_bin(
        carpeta=nueva, relativas={0: "C0001.MP4"},
        bytes_esperados={}, cuadros_esperados={},
        medir=lambda p: {"duration_frames": 0},
    )

    assert resultado.reconectados == {}
    assert resultado.sin_comprobar == [0]
    assert resultado.sin_confirmar == []
    assert resultado.no_encontrados == []


def test_el_tocayo_de_otra_tarjeta_si_es_sin_confirmar(tmp_path):
    """El unico caso en que se puede decir «no es el mismo video»: habia con
    que comprobarlo y no calzo."""
    nueva = tmp_path / "nueva"
    nueva.mkdir()
    (nueva / "C0001.MP4").write_bytes(b"x" * 111)

    resultado = reencontrar_bin(
        carpeta=nueva, relativas={0: "C0001.MP4"},
        bytes_esperados={0: 500}, cuadros_esperados={},
        medir=lambda p: {"duration_frames": 0},
    )

    assert resultado.sin_confirmar == [0]
    assert resultado.sin_comprobar == []
    assert resultado.disputados == []


def test_el_arbol_se_recorre_una_sola_vez(tmp_path, monkeypatch):
    """Con los 109 clips de una tarjeta de la Sony, uno por clip son 109
    barridos de 128 GB colgando la ventana."""
    nueva = tmp_path / "nueva"
    nueva.mkdir()
    for i in range(1, 6):
        (nueva / f"C000{i}.MP4").write_bytes(b"x" * 500)
    barridos = []
    original = Path.rglob

    def contar(self, patron, *args, **kwargs):
        barridos.append(patron)
        return original(self, patron, *args, **kwargs)

    monkeypatch.setattr(Path, "rglob", contar)

    reencontrar_bin(
        carpeta=nueva,
        relativas={i: f"vieja/C000{i}.MP4" for i in range(1, 6)},
        bytes_esperados={i: 500 for i in range(1, 6)},
        cuadros_esperados={},
        medir=lambda p: {"duration_frames": 0},
    )

    assert len(barridos) == 1


def test_la_duracion_guardada_en_segundos_se_vuelve_cuadros():
    """El proyecto guarda SEGUNDOS y `calza` compara CUADROS. Sin este
    puente, o media confirmacion no se cablea nunca, o alguien pasa segundos
    donde van cuadros y entonces no confirma jamas nada."""
    assert cuadros_esperados_de({0: 10.0}, {0: 30.0}) == {0: 300}


def test_redondea_igual_que_el_proxy():
    """Mismo criterio que `_el_proxy_calza`, que ya compara asi contra el
    original: `round(segundos * fps)`."""
    assert cuadros_esperados_de({0: 3.98}, {0: 29.97}) == {0: 119}


def test_sin_fps_no_se_inventan_cuadros():
    """Mejor confirmar solo por peso que comparar contra un numero
    inventado: eso rechazaria material bueno."""
    assert cuadros_esperados_de({0: 10.0}, {}) == {}
    assert cuadros_esperados_de({0: 10.0}, {0: 0}) == {}
    assert cuadros_esperados_de({0: "diez"}, {0: 30.0}) == {}


def test_las_llaves_pueden_venir_del_json_en_texto():
    """`duraciones` sale del `.cvproj`, donde toda llave es texto, y los fps
    salen de los clips en memoria, donde son enteros. Si no se cruzan, esto
    devuelve vacio en silencio y nada se confirma nunca por duracion."""
    assert cuadros_esperados_de({"0": 10.0}, {0: 30.0}) == {0: 300}
