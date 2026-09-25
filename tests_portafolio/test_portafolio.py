"""El portafolio único que crece para siempre: proyectos, clips y persistencia."""
from pathlib import Path

from clasificador_video_portafolio import portafolio as pf
from clasificador_video_portafolio.lector_de_entregas import ClipUsado, RangoUsado


def test_subir_de_sin_decidir_a_elegida():
    clip = pf.ClipDelPortafolio(ruta_origen=Path("x.mov"), proyecto="P")

    pf.subir(clip)

    assert clip.estado == "elegida"


def test_subir_dos_veces_seguidas_se_queda_en_elegida():
    clip = pf.ClipDelPortafolio(ruta_origen=Path("x.mov"), proyecto="P")

    pf.subir(clip)
    pf.subir(clip)

    assert clip.estado == "elegida"


def test_bajar_de_elegida_regresa_a_sin_decidir_primero():
    clip = pf.ClipDelPortafolio(
        ruta_origen=Path("x.mov"), proyecto="P", estado="elegida"
    )

    pf.bajar(clip)

    assert clip.estado == "sin_decidir"


def test_bajar_de_sin_decidir_llega_a_descartada():
    clip = pf.ClipDelPortafolio(ruta_origen=Path("x.mov"), proyecto="P")

    pf.bajar(clip)

    assert clip.estado == "descartada"


def test_bajar_no_pasa_de_descartada():
    clip = pf.ClipDelPortafolio(
        ruta_origen=Path("x.mov"), proyecto="P", estado="descartada"
    )

    pf.bajar(clip)

    assert clip.estado == "descartada"


def test_portafolio_nuevo_empieza_vacio():
    p = pf.Portafolio()

    assert p.proyectos == []


def test_categorias_conocidas_por_defecto():
    p = pf.Portafolio()

    assert "Casa" in p.categorias_conocidas
    assert "Depto" in p.categorias_conocidas


def test_asignar_categoria_nueva_la_agrega_a_las_conocidas(tmp_path):
    p = pf.Portafolio()
    proyecto = p.agregar_proyecto("Rancho", tmp_path / "r.prproj", [])

    p.asignar_categoria(proyecto, "Rancho")

    assert proyecto.categoria == "Rancho"
    assert "Rancho" in p.categorias_conocidas


def test_guardar_y_cargar_conserva_categorias_conocidas(tmp_path):
    portafolio = pf.Portafolio()
    proyecto = portafolio.agregar_proyecto("Rancho", tmp_path / "r.prproj", [])
    portafolio.asignar_categoria(proyecto, "Rancho")
    destino = tmp_path / "Mi Portafolio.cvportafolio"

    portafolio.guardar(destino)
    cargado = pf.Portafolio.cargar(destino)

    assert cargado.categorias_conocidas == ["Casa", "Depto", "Terreno", "Oficina", "Rancho"]


def test_cargar_archivo_anterior_usa_categorias_por_defecto(tmp_path):
    destino = tmp_path / "Portafolio anterior.cvportafolio"
    destino.write_text('{"proyectos": []}', encoding="utf-8")

    cargado = pf.Portafolio.cargar(destino)

    assert cargado.categorias_conocidas == ["Casa", "Depto", "Terreno", "Oficina"]


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


def test_alternar_etiqueta_la_agrega():
    clip = pf.ClipDelPortafolio(ruta_origen=Path("x.mov"), proyecto="P")

    pf.alternar_etiqueta(clip, "Dron")

    assert clip.etiquetas == ["Dron"]


def test_alternar_etiqueta_dos_veces_la_quita():
    clip = pf.ClipDelPortafolio(ruta_origen=Path("x.mov"), proyecto="P")

    pf.alternar_etiqueta(clip, "Dron")
    pf.alternar_etiqueta(clip, "Dron")

    assert clip.etiquetas == []


def test_un_clip_puede_tener_varias_etiquetas():
    clip = pf.ClipDelPortafolio(ruta_origen=Path("x.mov"), proyecto="P")

    pf.alternar_etiqueta(clip, "Dron")
    pf.alternar_etiqueta(clip, "Exteriores")

    assert set(clip.etiquetas) == {"Dron", "Exteriores"}


def test_elegidas_con_etiquetas_solo_devuelve_elegidas(tmp_path):
    p = pf.Portafolio()
    proyecto = p.agregar_proyecto("Casa", tmp_path / "c.prproj", [])
    c1 = pf.ClipDelPortafolio(tmp_path / "a.mov", "Casa", estado="elegida", etiquetas=["Dron"])
    c2 = pf.ClipDelPortafolio(tmp_path / "b.mov", "Casa", estado="elegida", etiquetas=["Cocina"])
    c3 = pf.ClipDelPortafolio(tmp_path / "c.mov", "Casa", estado="sin_decidir", etiquetas=["Dron"])
    proyecto.clips.extend([c1, c2, c3])

    filtrados = p.elegidas_con_etiquetas({"Dron"})

    assert filtrados == [c1]  # c3 no cuenta: no está Elegida


def test_elegidas_con_etiquetas_vacio_devuelve_todas_las_elegidas(tmp_path):
    p = pf.Portafolio()
    proyecto = p.agregar_proyecto("Casa", tmp_path / "c.prproj", [])
    c1 = pf.ClipDelPortafolio(tmp_path / "a.mov", "Casa", estado="elegida")
    c2 = pf.ClipDelPortafolio(tmp_path / "b.mov", "Casa", estado="descartada")
    proyecto.clips.extend([c1, c2])

    assert p.elegidas_con_etiquetas(set()) == [c1]
