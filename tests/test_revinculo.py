from clasificador_video.revinculo import calza


def test_NO_calza_un_tocayo_de_otro_tamano(tmp_path):
    """EL test de este plan. Un archivo con el nombre correcto y el
    contenido equivocado no se engancha. Es el caso de dos tarjetas de la
    misma camara, que numeran igual desde cero.
    """
    archivo = tmp_path / "C0001.MP4"
    archivo.write_bytes(b"x" * 999)

    assert calza(archivo, tamano_esperado=500, cuadros_esperados=300,
                 medir=lambda p: {"duration_frames": 300}) is False


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
