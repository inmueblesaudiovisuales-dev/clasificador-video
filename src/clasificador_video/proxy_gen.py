"""Generar proxies desde el original, con el codificador del chip.

Existe por el dron: la Sony escribe sus proxies sola (`C0001S03.MP4`) y el
DJI tambien escribe algo --el `.LRF`-- pero **ese no sirve**. Se midio contra
las 23 tomas reales de Bruno: el `.LRF` esta corrido entre 0 y 5 cuadros
respecto al original, y el desfase cambia de toma en toma. Para *ver* da
igual; para marcar in/out, no. Detalle en el handoff de los bins, §4.b.

Lo que si funciona, medido sobre el mismo material: **285 MB → 17 MB con los
1010 cuadros exactos**, a unos 10 s por cada 6 s de video.

Este modulo no sabe nada de Qt ni de la ventana. Arma el comando, dice donde
va el archivo y corre el proceso; quien lo llama desde un hilo y quien pinta
el avance es `MainWindow`.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from clasificador_video.binarios import ruta_de

# El lado corto del proxy. 720 es lo que se midio y lo que la app ya
# reproduce comodo; el lado LARGO sale de la proporcion del original, asi
# que un clip vertical da 720x1280 y no al reves.
LADO_CORTO = 720

# Los proxies generados terminan igual que los de la Sony. No es cosmetica:
# `ingest.es_archivo_de_proxy` descarta por ese sufijo, asi que si algun dia
# alguien arrastra la carpeta de proxies como si fuera material, no entra
# nada duplicado.
SUFIJO = "S03"

CARPETA = "Proxies"

# El nombre de la carpeta hermana donde van. Bruno lo eligio asi el
# 2026-08-10: «al lado». Es ademas como llegan de la camara --`sample-media`
# separa `clips/` de `proxy/`-- y como la app ya busca en las carpetas
# hermanas, los vuelve a encontrar sola la proxima vez, aunque sea en otro
# proyecto.


def carpeta_de_proxies(carpeta_del_bin: Path) -> Path:
    """Al lado de la carpeta del material, no adentro.

    Adentro ensuciaria la copia de la tarjeta, que es justo lo que uno
    quiere poder volver a copiar tal cual.
    """
    return carpeta_del_bin.parent / CARPETA


def ruta_de_proxy(original: Path, carpeta: Path) -> Path:
    """Siempre `.mp4`, sea cual sea la extension del original: el proxy lo
    escribimos nosotros y lo escribimos en un solo formato."""
    return carpeta / f"{original.stem}{SUFIJO}.mp4"


def comando(original: Path, destino: Path, ffmpeg: str | None = None) -> list[str]:
    """El comando de ffmpeg, armado aparte para poder probarlo sin correrlo.

    Los dos detalles que costaron una medicion equivocada y no se pueden
    perder:

    - **`-map 0:v:0`.** Los MP4 del dron traen una miniatura JPEG incrustada
      como SEGUNDA pista de video. Sin esto, ffmpeg elige esa por ser la de
      mejor "calidad" y sale un proxy de 406 px de ancho.
    - **El escalado mira cual lado es el corto.** `scale=-2:720` a secas
      deja un clip vertical en 720 de ANCHO, o sea 720x1280 cuando deberia
      ser 405x720. El `-2` mantiene la proporcion y ademas obliga a un
      numero par, que H.264 necesita.
    """
    escala = (
        f"scale='if(gt(iw,ih),-2,{LADO_CORTO})':'if(gt(iw,ih),{LADO_CORTO},-2)'"
    )
    return [
        ffmpeg or str(ruta_de("ffmpeg")),
        "-y",                       # el destino ya se comprobo antes de llamar
        "-i", str(original),
        "-map", "0:v:0",            # el video de verdad, no la miniatura
        "-map", "0:a?",             # el audio si lo hay, y sin fallar si no
        "-vf", escala,
        "-c:v", "h264_videotoolbox",  # el codificador del chip: sin el, 10x mas lento
        "-b:v", "6M",
        # A AAC y no `copy`: el audio del original puede venir en PCM, que no
        # cabe en un MP4 -- y ahi ffmpeg falla al final de la codificacion,
        # despues de haber gastado todo el tiempo.
        "-c:a", "aac", "-b:a", "128k",
        # Explicito porque el archivo se escribe como `...mp4.parcial` y
        # ffmpeg deduce el formato de la extension: sin esto falla con
        # «Error opening output files: Invalid argument», que no dice nada
        # sobre la verdadera causa. Comprobado en vivo.
        "-f", "mp4",
        str(destino),
    ]


def faltantes(originales: list[Path], carpeta: Path) -> list[Path]:
    """Los que todavia no tienen proxy en esa carpeta.

    Volver a darle a «Crear proxies» no rehace lo ya hecho: con 23 tomas del
    dron eso serian varios minutos tirados, y es el caso normal despues de
    cancelar a la mitad.
    """
    return [o for o in originales if not ruta_de_proxy(o, carpeta).exists()]


def generar(original: Path, carpeta: Path, ffmpeg: str | None = None) -> Path:
    """Genera UN proxy y devuelve su ruta. Levanta si ffmpeg falla.

    Escribe a un nombre temporal y renombra al final. Sin eso, cancelar o
    quedarse sin disco a la mitad deja un `.mp4` truncado con el nombre
    bueno -- y la proxima corrida lo daria por hecho y lo engancharia. Un
    proxy a medias es peor que ninguno: se ve, y miente sobre donde termina
    el clip.
    """
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = ruta_de_proxy(original, carpeta)
    parcial = destino.with_name(destino.name + ".parcial")
    resultado = subprocess.run(
        comando(original, parcial, ffmpeg),
        capture_output=True, text=True,
    )
    if resultado.returncode != 0 or not parcial.exists():
        parcial.unlink(missing_ok=True)
        cola = (resultado.stderr or "").strip().splitlines()
        raise RuntimeError(
            f"ffmpeg no pudo generar el proxy de {original.name}: "
            + (cola[-1] if cola else f"código {resultado.returncode}")
        )
    parcial.replace(destino)
    return destino
