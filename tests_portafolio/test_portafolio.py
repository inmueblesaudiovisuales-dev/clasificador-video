"""El portafolio único que crece para siempre: proyectos, clips y persistencia."""
from pathlib import Path

from clasificador_video_portafolio import portafolio as pf
from clasificador_video_portafolio.lector_de_entregas import ClipUsado, RangoUsado


def test_portafolio_nuevo_empieza_vacio():
    p = pf.Portafolio()

    assert p.proyectos == []


def test_agregar_proyecto_lo_registra_con_su_prproj_de_origen(tmp_path):
    p = pf.Portafolio()
    ruta_prproj = tmp_path / "Casa Reforma — entrega final.prproj"
    clips = [ClipUsado(tmp_path / "clip_014.mov", [RangoUsado(0, 100, "Secuencia 1")])]

    proyecto = p.agregar_proyecto("Casa Reforma", ruta_prproj, clips)

    assert proyecto in p.proyectos
    assert proyecto.nombre == "Casa Reforma"
    assert len(proyecto.clips) == 1
    assert proyecto.categoria is None


def test_guardar_y_cargar_redondo_conserva_el_rango_usado(tmp_path):
    p = pf.Portafolio()
    ruta_prproj = tmp_path / "Casa Reforma.prproj"
    clips = [ClipUsado(tmp_path / "clip_014.mov", [RangoUsado(0, 100, "Secuencia 1")])]
    p.agregar_proyecto("Casa Reforma", ruta_prproj, clips)
    destino = tmp_path / "Mi Portafolio.cvportafolio"

    p.guardar(destino)
    cargado = pf.Portafolio.cargar(destino)

    clip = cargado.proyectos[0].clips[0]
    assert clip.ruta_origen == tmp_path / "clip_014.mov"
    assert clip.rangos == [RangoUsado(0, 100, "Secuencia 1")]


def test_cargar_archivo_que_no_existe_da_portafolio_vacio(tmp_path):
    cargado = pf.Portafolio.cargar(tmp_path / "no existe.cvportafolio")

    assert cargado.proyectos == []


def test_reimportar_actualiza_rangos_sin_perder_estado_ni_etiquetas(tmp_path):
    portafolio = pf.Portafolio()
    ruta = tmp_path / "Casa Reforma.prproj"
    proyecto = portafolio.agregar_proyecto(
        "Casa Reforma", ruta,
        [ClipUsado(tmp_path / "clip_014.mov", [RangoUsado(0, 100, "Corte 1")])],
    )
    proyecto.clips[0].estado = "elegida"
    proyecto.clips[0].etiquetas = ["cocina"]

    portafolio.agregar_proyecto(
        "Casa Reforma", ruta,
        [ClipUsado(tmp_path / "clip_014.mov", [RangoUsado(50, 200, "Corte 2")])],
    )

    assert proyecto.clips[0].rangos == [RangoUsado(50, 200, "Corte 2")]
    assert proyecto.clips[0].estado == "elegida"
    assert proyecto.clips[0].etiquetas == ["cocina"]


def test_medios_faltantes_de_un_proyecto(tmp_path):
    portafolio = pf.Portafolio()
    clips = [
        ClipUsado(tmp_path / "existe.mov", []),
        ClipUsado(tmp_path / "no_existe.mov", []),
    ]
    (tmp_path / "existe.mov").write_text("x")
    proyecto = portafolio.agregar_proyecto("Depto Polanco", tmp_path / "Depto Polanco.prproj", clips)

    faltantes = portafolio.medios_faltantes_de(proyecto)

    assert [clip.ruta_origen.name for clip in faltantes] == ["no_existe.mov"]


def test_revincular_actualiza_solo_si_encuentra_el_mismo_archivo(tmp_path):
    clip = pf.ClipDelPortafolio(tmp_path / "desconectado" / "clip_014.mov", "Casa")
    carpeta_nueva = tmp_path / "SSD nuevo"
    carpeta_nueva.mkdir()
    encontrada = carpeta_nueva / "clip_014.mov"
    encontrada.write_text("material")

    resultado = pf.Portafolio().revincular(clip, carpeta_nueva)

    assert resultado is True
    assert clip.ruta_origen == encontrada
