"""Nombres de clips en el proyecto de Premiere."""
from clasificador_video.nombre_de_clip import nombre_de_clip, numeros_de_clip


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
