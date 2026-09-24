"""Nombres de clips en el proyecto de Premiere."""
from clasificador_video.nombre_de_clip import (
    anchos_de_clip, nombre_de_clip, numeros_de_clip,
)


def test_nombre_de_clip_usa_mayusculas_guion_y_marca_despues_del_numero():
    assert nombre_de_clip("Cocina", 1, "DRONE", "pick") == "COCINA-01 ✓ [DRONE]"


def test_nombre_de_clip_reject():
    assert nombre_de_clip("Cocina", 3, "SONY", "reject") == "COCINA-03 ✕ [SONY]"


def test_nombre_de_clip_destacado():
    assert nombre_de_clip("Cocina", 2, "", "destacado") == "COCINA-02 ★"


def test_nombre_de_clip_sin_marca_no_deja_espacio_extra():
    assert nombre_de_clip("Baño", 123, "SONY", "none") == "BAÑO-123 [SONY]"


def test_nombre_de_clip_numero_pasa_de_dos_digitos():
    assert nombre_de_clip("Cocina", 123, "", "none") == "COCINA-123"


def test_numeros_de_clip_cuenta_por_cuarto_en_orden():
    clips = [{"categoria_path": ["Cocina"]}, {"categoria_path": ["Bano"]}, {"categoria_path": ["Cocina"]}]
    assert numeros_de_clip(clips) == [1, 1, 2]


def test_numeros_de_clip_dos_unidades_con_mismo_cuarto_no_comparten_contador():
    clips = [{"categoria_path": ["Casa A", "Cocina"]}, {"categoria_path": ["Casa B", "Cocina"]}]
    assert numeros_de_clip(clips) == [1, 1]


def test_nombre_de_clip_con_ancho_rellena_a_tres_digitos():
    assert nombre_de_clip("Cocina", 9, "SONY", "none", ancho=3) == "COCINA-009 [SONY]"


def test_anchos_de_clip_sube_a_tres_digitos_pasando_de_99_clips_en_el_cuarto():
    """Con dos dígitos fijos, el clip 100 ordena ANTES que el 99 -- "100" es
    menor que "99" letra por letra. El ancho tiene que crecer con el total
    de ese cuarto para que el orden alfabético en Premiere siga siendo el
    cronológico."""
    clips = [{"categoria_path": ["Cocina"]}] * 100 + [{"categoria_path": ["Bano"]}] * 3
    anchos = anchos_de_clip(clips)
    assert anchos[:100] == [3] * 100
    assert anchos[100:] == [2] * 3
    numeros = numeros_de_clip(clips)
    nombres = [nombre_de_clip("Cocina", numeros[i], "", "none", ancho=anchos[i])
               for i in range(100)]
    assert sorted(nombres) == nombres


def test_anchos_de_clip_se_queda_en_dos_digitos_hasta_99():
    clips = [{"categoria_path": ["Cocina"]}] * 99
    assert anchos_de_clip(clips) == [2] * 99
