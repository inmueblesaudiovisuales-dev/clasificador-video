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
