import json
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


def test_una_escritura_fallida_no_deja_basura(tmp_path, monkeypatch):
    """Mismo criterio que `proyecto.guardar`: temporal + rename. Si la app
    muere a medio escribir, la lista queda con lo viejo completo en vez de
    perderse entera, que es lo que hacia `write_text` --trunca y despues
    escribe."""
    archivo = tmp_path / "recientes.json"
    Recientes(archivo).registrar(Path("/a/uno.cvproj"), "Uno")
    original = Path.write_text

    def se_llena_el_disco(self, texto, *args, **kwargs):
        original(self, texto[:5])
        raise OSError("No space left on device")

    monkeypatch.setattr(Path, "write_text", se_llena_el_disco)
    Recientes(archivo).registrar(Path("/a/dos.cvproj"), "Dos")
    monkeypatch.undo()

    assert [e.nombre for e in Recientes(archivo).lista()] == ["Uno"]
    assert not (tmp_path / "recientes.json.tmp").exists()


def test_no_poder_escribir_no_impide_abrir_el_proyecto(tmp_path):
    """`registrar` se llama DENTRO de abrir y crear proyecto. Si tronara
    con la carpeta sin permiso, una comodidad rota impediria abrir."""
    estorbo = tmp_path / "estorbo"
    estorbo.write_text("no soy una carpeta")

    Recientes(estorbo / "recientes.json").registrar(Path("/a/uno.cvproj"), "Uno")


def test_no_se_muestran_repetidos_aunque_el_archivo_los_traiga(tmp_path):
    archivo = tmp_path / "recientes.json"
    archivo.write_text(json.dumps([
        {"ruta": "/a/uno.cvproj", "nombre": "Uno", "cuando": "hoy"},
        {"ruta": "/a/uno.cvproj", "nombre": "Uno otra vez", "cuando": "ayer"},
    ]))

    assert [e.nombre for e in Recientes(archivo).lista()] == ["Uno"]


def test_estar_disponible_se_averigua_una_sola_vez(tmp_path):
    """El caso que motiva esto es un disco de red colgado, donde `exists()`
    puede bloquear segundos -- y esto se lee en el hilo de la interfaz, al
    arrancar. Se mira el disco al leer la lista y no en cada consulta."""
    existe = tmp_path / "esta.cvproj"
    existe.write_text("{}")
    r = Recientes(tmp_path / "recientes.json")
    r.registrar(existe, "Esta")

    entrada = r.lista()[0]
    existe.unlink()

    assert entrada.disponible is True


def test_lo_que_otro_registro_no_se_pierde(tmp_path):
    """La pantalla de inicio y la ventana abierta tienen su propia
    instancia. Si cada una escribiera lo que tenia en memoria, la ultima en
    guardar borraria lo que apunto la otra."""
    archivo = tmp_path / "recientes.json"
    uno = Recientes(archivo)
    uno.registrar(Path("/a/uno.cvproj"), "Uno")
    Recientes(archivo).registrar(Path("/a/dos.cvproj"), "Dos")

    uno.registrar(Path("/a/tres.cvproj"), "Tres")

    assert [e.nombre for e in uno.lista()] == ["Tres", "Dos", "Uno"]
