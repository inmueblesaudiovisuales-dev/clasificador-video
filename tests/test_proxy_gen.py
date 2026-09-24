# tests/test_proxy_gen.py
import subprocess
from pathlib import Path

import pytest

from clasificador_video import proxy_gen


def test_la_carpeta_de_antes_seguia_al_lado_del_material():
    """Hasta el 2026-08-22 los proxies iban AL LADO, y Bruno lo eligio asi
    para no ensuciar la copia de la tarjeta. Se revirtio a proposito --ahora
    van adentro, para que viajen con el material-- pero la ubicacion vieja
    tiene que seguir existiendo: es donde estan los proxies de todos sus
    proyectos anteriores.
    """
    material = Path("/tarjeta/01. VIDEOS SONY")

    assert proxy_gen.carpeta_al_lado(material) == Path("/tarjeta/Proxies")


def test_ruta_de_proxy_termina_en_proxy(tmp_path):
    """El sufijo `S03` no es cosmetica: `ingest.es_archivo_de_proxy` descarta
    por el, asi que arrastrar la carpeta de proxies como si fuera material no
    duplica nada."""
    destino = proxy_gen.ruta_de_proxy(tmp_path / "C0001.MP4", tmp_path)

    assert destino == tmp_path / "C0001_proxy.mp4"


def test_el_comando_toma_la_primera_pista_de_video():
    """Los MP4 del dron traen una miniatura JPEG incrustada como SEGUNDA
    pista de video. Sin `-map 0:v:0` ffmpeg transcodifica ESA --la elige por
    ser la de mejor "calidad"-- y sale un proxy de 406 px de ancho. Costo una
    medicion entera descubrirlo."""
    args = proxy_gen.comando(Path("a.MP4"), Path("b.mp4"), ffmpeg="ffmpeg")

    assert "-map" in args
    assert args[args.index("-map") + 1] == "[v]"


def test_el_comando_ya_no_escala___sale_al_tamano_real_del_original():
    """El proxy deja de achicar el cuadro (spec 2026-09-18 §2): un clip de
    4K da un proxy de 4K. Se abandonó 720p porque un editor externo que
    reencuadra sobre un proxy de OTRO tamaño calcula el ajuste mal, y al
    reconectar contra el original la imagen sale chica y cortada --
    comprobado con capturas reales, no en teoría."""
    args = proxy_gen.comando(Path("a.MP4"), Path("b.mp4"), ffmpeg="ffmpeg")

    assert "-vf" not in args


def test_comando_superpone_la_marca_sin_escalar_ni_rotar(tmp_path):
    args = proxy_gen.comando(tmp_path / "C0001.MP4", tmp_path / "C0001_proxy.mp4")

    filtro = args[args.index("-filter_complex") + 1]
    assert "overlay=W-w-" in filtro
    assert "scale" not in filtro and "transpose" not in filtro and "setpts" not in filtro
    assert "-loop" not in args


def test_el_comando_no_falla_si_el_clip_no_trae_audio():
    """El `?` de `0:a?`. Sin el, un clip mudo --pasa con el dron-- aborta
    ffmpeg antes de empezar."""
    args = proxy_gen.comando(Path("a.MP4"), Path("b.mp4"), ffmpeg="ffmpeg")

    assert "0:a?" in args


def test_faltantes_deja_fuera_los_que_ya_tienen_proxy(tmp_path):
    """Volver a darle a «Crear proxies» no rehace lo hecho. Es el caso normal
    despues de cancelar a la mitad: con 23 tomas, rehacerlas son minutos
    tirados."""
    proxies = tmp_path / "Proxies"
    proxies.mkdir()
    (proxies / "DJI_0001S03.mp4").touch()
    originales = [Path("/m/DJI_0001.MP4"), Path("/m/DJI_0002.MP4")]

    assert proxy_gen.faltantes(originales, proxies) == [Path("/m/DJI_0002.MP4")]


class _FfmpegFalso:
    """Un `Popen` de mentira: escribe el archivo de salida y termina.

    `vueltas_colgado` simula un ffmpeg que tarda: `communicate` levanta
    `TimeoutExpired` esas veces antes de devolver, que es cuando la funcion
    consulta si la cancelaron.
    """

    def __init__(self, args, vueltas_colgado=0, returncode=0, stderr="", **kwargs):
        self._destino = Path(args[-1])
        self._faltan = vueltas_colgado
        self.returncode = returncode
        self._stderr = stderr
        self.terminado = False

    def communicate(self, timeout=None):
        if self._faltan > 0:
            self._faltan -= 1
            raise subprocess.TimeoutExpired(cmd="ffmpeg", timeout=timeout)
        if self.returncode == 0:
            self._destino.write_bytes(b"video")
        return "", self._stderr

    def terminate(self):
        self.terminado = True

    def wait(self, timeout=None):
        return self.returncode

    def kill(self):
        self.terminado = True


def test_generar_escribe_a_un_parcial_y_renombra_al_final(tmp_path, monkeypatch):
    """Sin el temporal, cancelar o quedarse sin disco a la mitad deja un mp4
    truncado CON EL NOMBRE BUENO -- y la corrida siguiente lo da por hecho y
    lo engancha. Un proxy a medias es peor que ninguno: se ve, y miente sobre
    donde termina el clip."""
    vistos = []

    def falso_popen(args, **kwargs):
        vistos.append(Path(args[-1]).name)
        return _FfmpegFalso(args)

    monkeypatch.setattr(proxy_gen.subprocess, "Popen", falso_popen)

    destino = proxy_gen.generar(Path("/m/DJI_0001.MP4"), tmp_path / "Proxies",
                                ffmpeg="ffmpeg")

    assert vistos == ["DJI_0001_proxy.mp4.parcial"]   # ffmpeg escribio al temporal
    assert destino.name == "DJI_0001_proxy.mp4"       # y quedo con el nombre bueno
    assert destino.exists()


def test_si_ffmpeg_falla_no_queda_basura_ni_se_dice_que_si(tmp_path, monkeypatch):
    monkeypatch.setattr(
        proxy_gen.subprocess, "Popen",
        lambda args, **k: _FfmpegFalso(
            args, returncode=1, stderr="Invalid data found when processing input"),
    )
    carpeta = tmp_path / "Proxies"

    with pytest.raises(RuntimeError, match="Invalid data"):
        proxy_gen.generar(Path("/m/DJI_0001.MP4"), carpeta, ffmpeg="ffmpeg")

    assert list(carpeta.iterdir()) == []


def test_cancelar_corta_ffmpeg_en_vez_de_esperarlo(tmp_path, monkeypatch):
    """Antes esto era una llamada que no se podia interrumpir: al cerrar la
    app durante una tanda, la ventana se quedaba congelada hasta que
    terminara el clip en curso -- y con una toma de dron de tres minutos y
    medio, eso son varios minutos mirando una app muerta."""
    procesos = []

    def falso_popen(args, **kwargs):
        proceso = _FfmpegFalso(args, vueltas_colgado=10)
        procesos.append(proceso)
        return proceso

    monkeypatch.setattr(proxy_gen.subprocess, "Popen", falso_popen)
    carpeta = tmp_path / "Proxies"

    with pytest.raises(proxy_gen.Interrumpido):
        proxy_gen.generar(Path("/m/DJI_0001.MP4"), carpeta, ffmpeg="ffmpeg",
                          cancelado=lambda: True, latido=0.001)

    assert procesos[0].terminado                 # se le corto, no se espero
    assert list(carpeta.iterdir()) == []         # y no quedo el .parcial


def test_barrer_parciales_se_lleva_los_pedazos(tmp_path):
    """Un `.parcial` es un proxy a medias de una tanda que se corto de golpe.
    `generar` los borra al cancelar, pero un cierre forzado o un corte de luz
    los deja ahi, y nadie los recoge nunca."""
    (tmp_path / "C0001S03.mp4.parcial").write_bytes(b"x")
    (tmp_path / "C0002S03.mp4.parcial").write_bytes(b"x")

    barridos = proxy_gen.barrer_parciales(tmp_path)

    assert barridos == 2
    assert list(tmp_path.iterdir()) == []


def test_barrer_parciales_no_toca_los_proxies_buenos(tmp_path):
    """Lo unico que se va son los pedazos. Un proxy terminado es el trabajo
    de varios minutos que esta tanda existe para no repetir."""
    bueno = tmp_path / "C0001S03.mp4"
    bueno.write_bytes(b"proxy de verdad")
    (tmp_path / "C0002S03.mp4.parcial").write_bytes(b"x")

    proxy_gen.barrer_parciales(tmp_path)

    assert bueno.exists()
    assert not (tmp_path / "C0002S03.mp4.parcial").exists()


def test_barrer_parciales_aguanta_una_carpeta_que_no_esta(tmp_path):
    """Se llama al empezar la tanda de un bin, y ese bin puede apuntar a una
    tarjeta desconectada. Que no exista no es un error: no hay nada que
    barrer."""
    assert proxy_gen.barrer_parciales(tmp_path / "no existe") == 0


# --- los proxies adentro (spec 2026-08-22-proxies-adentro-design) ---------


def test_los_proxies_nuevos_van_adentro_de_la_carpeta_del_material(tmp_path):
    """Cambio del 2026-08-22, pedido por Bruno: asi los proxies VIAJAN con el
    material cuando mueve la carpeta, en vez de quedarse huerfanos al lado."""
    material = tmp_path / "01. VIDEOS SONY"
    material.mkdir()

    assert proxy_gen.carpeta_de_proxies(material) == material / "Proxies"


def test_la_carpeta_de_antes_sigue_teniendo_nombre(tmp_path):
    """Los proyectos de antes del 2026-08-22 la tienen al lado, y hay que
    poder nombrarla para seguir encontrandolos."""
    material = tmp_path / "01. VIDEOS SONY"
    material.mkdir()

    assert proxy_gen.carpeta_al_lado(material) == tmp_path / "Proxies"


def test_un_proxy_de_antes_se_encuentra_donde_estaba(tmp_path):
    """Lo que hace el cambio retrocompatible: un proyecto viejo abre igual,
    sin regenerar nada."""
    material = tmp_path / "clips"
    material.mkdir()
    original = material / "C0001.MP4"
    original.write_bytes(b"x")
    al_lado = tmp_path / "Proxies"
    al_lado.mkdir()
    viejo = proxy_gen.ruta_de_proxy(original, al_lado)
    viejo.write_bytes(b"proxy")

    assert proxy_gen.ruta_de_proxy_existente(original, material) == viejo


def test_si_esta_en_los_dos_lados_gana_el_de_adentro(tmp_path):
    """Adentro es donde van los nuevos: si hay uno ahi, es el que se acaba de
    hacer."""
    material = tmp_path / "clips"
    material.mkdir()
    original = material / "C0001.MP4"
    original.write_bytes(b"x")
    for carpeta in (tmp_path / "Proxies", material / "Proxies"):
        carpeta.mkdir()
        proxy_gen.ruta_de_proxy(original, carpeta).write_bytes(b"proxy")

    encontrado = proxy_gen.ruta_de_proxy_existente(original, material)

    assert encontrado.parent == material / "Proxies"


def test_sin_proxy_en_ninguno_de_los_dos_no_se_encuentra_nada(tmp_path):
    material = tmp_path / "clips"
    material.mkdir()
    original = material / "C0001.MP4"
    original.write_bytes(b"x")

    assert proxy_gen.ruta_de_proxy_existente(original, material) is None


def test_si_no_se_puede_escribir_adentro_se_escribe_al_lado(tmp_path):
    """El material puede estar en una tarjeta protegida o llena. Quedarse sin
    proxies por donde iba a ir la carpeta seria peor que ponerla un nivel
    arriba, que es donde funcionaban hasta ayer."""
    material = tmp_path / "clips"
    material.mkdir()
    material.chmod(0o500)                       # se puede leer, no escribir
    try:
        assert proxy_gen.carpeta_para_escribir(material) == tmp_path / "Proxies"
    finally:
        material.chmod(0o700)


def test_si_se_puede_escribir_adentro_se_escribe_adentro(tmp_path):
    material = tmp_path / "clips"
    material.mkdir()

    assert proxy_gen.carpeta_para_escribir(material) == material / "Proxies"


# --------------------------------------------------------------------------
# La carpeta elegida (spec 2026-08-25). Los proxies nuevos van a una carpeta
# que Bruno escoge, con una SUBCARPETA por bin llamada igual que la carpeta
# del material.
# --------------------------------------------------------------------------


def test_subcarpeta_por_numero_encuentra_una_con_nombre_distinto(tmp_path):
    """Bruno ya tiene, hecha a mano, `02. PROXY DRONE` como hermana de
    `02. VIDEO DRONE` -- mismo número, nombre distinto a propósito. La
    regla de agosto (nombre IDÉNTICO) la ignoraba y creaba una carpeta
    nueva vacía al lado. Regla nueva: el número manda."""
    elegida = tmp_path / "Proxies del proyecto"
    elegida.mkdir()
    (elegida / "02. PROXY DRONE").mkdir()
    material = tmp_path / "material" / "02. VIDEO DRONE"
    material.mkdir(parents=True)

    destino = proxy_gen.subcarpeta_por_numero(elegida, material)

    assert destino == elegida / "02. PROXY DRONE"


def test_subcarpeta_por_numero_sin_coincidencia_usa_el_nombre_de_siempre(tmp_path):
    elegida = tmp_path / "Proxies del proyecto"
    elegida.mkdir()
    material = tmp_path / "material" / "02. VIDEO DRONE"
    material.mkdir(parents=True)

    destino = proxy_gen.subcarpeta_por_numero(elegida, material)

    assert destino == elegida / "02. VIDEO DRONE"


def test_subcarpeta_por_numero_sin_numero_en_el_material_usa_el_nombre(tmp_path):
    """Una carpeta de material sin prefijo numérico (`DRONE`, sin `02. `)
    no tiene número que comparar: se cae al comportamiento de siempre."""
    elegida = tmp_path / "Proxies del proyecto"
    elegida.mkdir()
    (elegida / "DRONE viejo").mkdir()
    material = tmp_path / "material" / "DRONE"
    material.mkdir(parents=True)

    destino = proxy_gen.subcarpeta_por_numero(elegida, material)

    assert destino == elegida / "DRONE"


def test_con_carpeta_elegida_los_nuevos_van_a_su_subcarpeta(tmp_path):
    material = tmp_path / "02. VIDEO DRONE"
    material.mkdir()
    elegida = tmp_path / "07. PROXIES"
    elegida.mkdir()

    assert (proxy_gen.carpeta_para_escribir(material, elegida=elegida)
            == elegida / "02. VIDEO DRONE")


def test_dos_bins_con_el_mismo_nombre_de_archivo_no_se_pisan(tmp_path):
    """El segundo problema que resuelve el spec: hoy todos los proxies caen
    revueltos en un solo monton. Dos tarjetas Sony pueden traer un `PIB0001`
    cada una, y uno pisaria al otro SIN AVISAR -- el mismo modo de falla de
    los proxies desenganchados.
    """
    elegida = tmp_path / "Proxies"
    sony_a = tmp_path / "TARJETA A"
    sony_b = tmp_path / "TARJETA B"
    for c in (sony_a, sony_b):
        c.mkdir()

    ruta_a = proxy_gen.ruta_de_proxy(
        sony_a / "PIB0001.MP4", proxy_gen.subcarpeta_por_numero(elegida, sony_a))
    ruta_b = proxy_gen.ruta_de_proxy(
        sony_b / "PIB0001.MP4", proxy_gen.subcarpeta_por_numero(elegida, sony_b))

    assert ruta_a != ruta_b


def test_la_carpeta_elegida_se_mira_primero_al_buscar(tmp_path):
    material = tmp_path / "material"
    material.mkdir()
    elegida = tmp_path / "07. PROXIES"
    original = material / "clip.MP4"
    original.touch()

    nueva = proxy_gen.subcarpeta_por_numero(elegida, material)
    nueva.mkdir(parents=True)
    proxy_gen.ruta_de_proxy(original, nueva).touch()

    assert (proxy_gen.ruta_de_proxy_existente(original, material, elegida=elegida)
            == proxy_gen.ruta_de_proxy(original, nueva))


def test_con_carpeta_elegida_los_de_antes_se_siguen_encontrando(tmp_path):
    """Retrocompatibilidad: elegir una carpeta NO invalida lo que ya existe.
    Bruno pidio explicitamente que a los proyectos que ya tiene no se les
    mueva un solo archivo.
    """
    material = tmp_path / "material"
    material.mkdir()
    original = material / "clip.MP4"
    original.touch()
    # uno de antes de la 1.10: al lado, suelto
    al_lado = proxy_gen.carpeta_al_lado(material)
    al_lado.mkdir(parents=True)
    proxy_gen.ruta_de_proxy(original, al_lado).touch()

    encontrado = proxy_gen.ruta_de_proxy_existente(
        original, material, elegida=tmp_path / "07. PROXIES")

    assert encontrado == proxy_gen.ruta_de_proxy(original, al_lado)


def test_sin_carpeta_elegida_todo_se_comporta_igual_que_antes(tmp_path):
    """El default no cambia para nadie: un proyecto que nunca contesto la
    pregunta sigue escribiendo adentro del material, como desde la 1.10."""
    material = tmp_path / "material"
    material.mkdir()

    assert (proxy_gen.carpeta_para_escribir(material)
            == proxy_gen.carpeta_de_proxies(material))


def test_si_la_carpeta_elegida_no_se_puede_escribir_se_cae_a_lo_de_hoy(tmp_path):
    """Quedarse sin proxies porque el disco de la carpeta elegida esta
    desconectado seria peor que ponerlos donde funcionaban ayer."""
    material = tmp_path / "material"
    material.mkdir()
    elegida = tmp_path / "disco que no esta" / "Proxies"

    assert (proxy_gen.carpeta_para_escribir(material, elegida=elegida)
            == proxy_gen.carpeta_de_proxies(material))


# --------------------------------------------------------------------------
# Lo que la app PROPONE cuando pregunta. Proponer esta bien; adivinar en
# silencio, no.
# --------------------------------------------------------------------------


def test_propone_la_carpeta_de_proxies_que_bruno_ya_tenia(tmp_path):
    """El caso real de `IAV-2608.17-A`: Bruno tenia `07. PROXIES` con sus
    subcarpetas hechas a mano, y la app le habia creado un `Proxies/` aparte.
    Se propone la de EL.

    `Proxies/` queda fuera de los candidatos a proposito: no es una
    convencion suya, es donde la propia app tiraba los archivos antes.
    """
    material = tmp_path / "02. VIDEO DRONE"
    material.mkdir()
    (tmp_path / "07. PROXIES").mkdir()
    (tmp_path / "Proxies").mkdir()       # el monton viejo de la app

    assert proxy_gen.proponer_carpeta(material) == tmp_path / "07. PROXIES"


def test_sin_ninguna_carpeta_de_proxies_propone_la_de_siempre(tmp_path):
    material = tmp_path / "material"
    material.mkdir()

    assert proxy_gen.proponer_carpeta(material) == tmp_path / proxy_gen.CARPETA


def test_con_carpeta_de_icloud_se_propone_esa_directo(tmp_path):
    material = tmp_path / "material"
    material.mkdir()
    (tmp_path / "07. PROXIES").mkdir()
    carpeta_de_icloud = tmp_path / "IAV-2609.10-A" / "03. Proxies"

    assert proxy_gen.proponer_carpeta(
        material, carpeta_de_icloud) == carpeta_de_icloud


def test_sin_carpeta_de_icloud_se_comporta_como_antes(tmp_path):
    material = tmp_path / "material"
    material.mkdir()
    (tmp_path / "07. PROXIES").mkdir()

    assert proxy_gen.proponer_carpeta(material, None) == tmp_path / "07. PROXIES"


def test_con_varias_candidatas_no_adivina(tmp_path):
    """Dos carpetas con «prox» en el nombre y no hay forma de saber cual.
    Se propone la de siempre y que Bruno decida: la ruta se le enseña
    igual antes de escribir nada."""
    material = tmp_path / "material"
    material.mkdir()
    (tmp_path / "07. PROXIES").mkdir()
    (tmp_path / "PROXIES VIEJOS").mkdir()

    assert proxy_gen.proponer_carpeta(material) == tmp_path / proxy_gen.CARPETA
