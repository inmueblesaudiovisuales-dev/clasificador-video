# tests/test_proxy_match.py
from pathlib import Path

from clasificador_video.proxy_match import (
    clip_del_proxy,
    emparejar_con_patron,
    etiqueta_de_resolucion,
    patron_de_proxy,
)


# --- enganche MANUAL, como en Premiere (pedido de Bruno) ---------------
#
# «Necesito que los proxies los ponga manualmente siempre, que sea un
# proceso como Premiere donde agarras un clip primero y luego se pone
# todo»: eliges el proxy de UN clip y de ahi sale el patron para los
# demas.


def test_deduce_el_sufijo_del_par_que_elegiste():
    patron = patron_de_proxy(Path("/cam/C0001.MP4"), Path("/px/C0001S03.MP4"))
    assert patron == ("", "S03")


def test_deduce_un_prefijo():
    patron = patron_de_proxy(Path("/cam/C0001.MP4"), Path("/px/PRX_C0001.MOV"))
    assert patron == ("PRX_", "")


def test_el_proxy_puede_llamarse_igual_en_otra_carpeta():
    assert patron_de_proxy(Path("/cam/C0001.MP4"), Path("/px/C0001.MP4")) == ("", "")


def test_si_el_nombre_no_tiene_nada_que_ver_no_hay_patron():
    """Elegiste el archivo equivocado: mejor decirlo que emparejar 128
    clips con un patron inventado."""
    assert patron_de_proxy(Path("/cam/C0001.MP4"), Path("/px/otra_cosa.MP4")) is None


def test_aplica_el_patron_a_todos_los_clips(tmp_path):
    proxies = tmp_path / "proxy"
    proxies.mkdir()
    for n in ("C0001S03.MP4", "C0002S03.MP4", "C0004S03.MP4"):
        (proxies / n).touch()
    originales = [Path(f"/cam/C{i:04d}.MP4") for i in (1, 2, 3, 4)]

    r = emparejar_con_patron(originales, proxies, "", "S03", ".MP4")

    assert r[originales[0]].name == "C0001S03.MP4"
    assert r[originales[2]] is None          # C0003 no tiene proxy
    assert r[originales[3]].name == "C0004S03.MP4"


def test_acepta_otra_extension_de_video(tmp_path):
    """La camara puede escribir el original en .MP4 y el proxy en .MOV."""
    proxies = tmp_path / "proxy"
    proxies.mkdir()
    (proxies / "C0001S03.MOV").touch()
    originales = [Path("/cam/C0001.MP4")]

    r = emparejar_con_patron(originales, proxies, "", "S03", ".MP4")

    assert r[originales[0]].name == "C0001S03.MOV"


def test_una_carpeta_que_ya_no_esta_no_revienta(tmp_path):
    r = emparejar_con_patron([Path("/cam/C0001.MP4")], tmp_path / "no-existe", "", "S03", ".MP4")
    assert r == {Path("/cam/C0001.MP4"): None}


def test_cualquier_proxy_del_bin_sirve_para_deducir_el_patron():
    """Bruno se topo con esto en su material: «cuando quiero ponerle proxies
    a un bin que ya tiene clips clasificados no puedo solo elegir el primer
    clip de la carpeta de proxies».

    El enganche pedia el proxy DEL CLIP EN EL QUE ESTABAS, y eso no se ve
    por ningun lado: abres el dialogo, ves 111 proxies ordenados por nombre
    y eliges el primero.
    """
    clips = [Path(f"/m/20260804_PIB{n}.MP4") for n in ("0587", "0654", "0700")]

    assert clip_del_proxy(clips, Path("/p/20260804_PIB0587S03.MP4")) == clips[0]
    assert clip_del_proxy(clips, Path("/p/20260804_PIB0700S03.MP4")) == clips[2]


def test_gana_el_nombre_mas_largo_que_calza():
    """`C0001` esta contenido en `C00011S03`. Con el corto se deduciria el
    sufijo `1S03` y los otros 110 clips se buscarian con un patron
    inventado."""
    clips = [Path("/m/C0001.MP4"), Path("/m/C00011.MP4")]

    assert clip_del_proxy(clips, Path("/p/C00011S03.MP4")) == Path("/m/C00011.MP4")


def test_un_archivo_ajeno_al_bin_no_calza_con_ninguno():
    """Mejor no enganchar nada que emparejar 111 clips con un patron
    inventado."""
    clips = [Path("/m/C0001.MP4"), Path("/m/C0002.MP4")]

    assert clip_del_proxy(clips, Path("/p/DJI_0001.MP4")) is None
