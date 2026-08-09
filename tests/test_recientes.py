from pathlib import Path

from clasificador_video.recientes import Recientes


def test_el_ultimo_abierto_queda_primero(tmp_path):
    r = Recientes(tmp_path / "recientes.json")
    r.registrar(Path("/a/uno.cvproj"), "Uno")
    r.registrar(Path("/a/dos.cvproj"), "Dos")

    assert [e.nombre for e in r.lista()] == ["Dos", "Uno"]


def test_volver_a_abrir_uno_lo_sube_sin_duplicarlo(tmp_path):
    r = Recientes(tmp_path / "recientes.json")
    r.registrar(Path("/a/uno.cvproj"), "Uno")
    r.registrar(Path("/a/dos.cvproj"), "Dos")
    r.registrar(Path("/a/uno.cvproj"), "Uno")

    assert [e.nombre for e in r.lista()] == ["Uno", "Dos"]


def test_se_guarda_y_se_vuelve_a_leer(tmp_path):
    archivo = tmp_path / "recientes.json"
    Recientes(archivo).registrar(Path("/a/uno.cvproj"), "Uno")

    assert [e.nombre for e in Recientes(archivo).lista()] == ["Uno"]


def test_un_archivo_corrupto_se_trata_como_lista_vacia(tmp_path):
    """Los recientes son una comodidad. Que un JSON roto impida ABRIR la
    app seria cambiar una comodidad por un ladrillo."""
    archivo = tmp_path / "recientes.json"
    archivo.write_text("{{{ no es json")

    assert Recientes(archivo).lista() == []


def test_dice_cuales_ya_no_estan_en_su_lugar(tmp_path):
    """No se podan solos: se muestran apagados. Bruno tiene que poder ver
    que el proyecto existio y que el disco no esta conectado, en vez de que
    desaparezca de la lista sin explicacion."""
    existe = tmp_path / "esta.cvproj"
    existe.write_text("{}")
    r = Recientes(tmp_path / "recientes.json")
    r.registrar(existe, "Esta")
    r.registrar(tmp_path / "no-esta.cvproj", "No esta")

    faltantes = [e for e in r.lista() if not e.disponible]
    assert [e.nombre for e in faltantes] == ["No esta"]


def test_se_puede_quitar_uno_de_la_lista(tmp_path):
    r = Recientes(tmp_path / "recientes.json")
    r.registrar(Path("/a/uno.cvproj"), "Uno")

    r.quitar(Path("/a/uno.cvproj"))

    assert r.lista() == []


def test_la_lista_no_crece_sin_limite(tmp_path):
    r = Recientes(tmp_path / "recientes.json")
    for i in range(15):
        r.registrar(Path(f"/a/{i}.cvproj"), f"P{i}")

    assert len(r.lista()) == 10
