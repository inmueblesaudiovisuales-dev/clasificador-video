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


SUFIJO_PARCIAL = ".parcial"


def barrer_parciales(carpeta: Path) -> int:
    """Borra los proxies a medias que hayan quedado, y dice cuantos eran.

    `generar` escribe a `<nombre>.mp4.parcial` y solo renombra al nombre
    bueno cuando ffmpeg termina bien, asi que un `.parcial` NUNCA bloquea a
    su clip: `ruta_de_proxy(...).exists()` no lo ve y el clip se vuelve a
    generar solo. O sea que esto no arregla nada roto -- limpia.

    Cancelar ya los borra. Los que quedan son de un cierre de golpe, un
    crash o un corte de luz, y ahi nadie los recoge: se van juntando en la
    carpeta del material de Bruno.

    **Cuando se llama importa:** al EMPEZAR la tanda de un bin, que es el
    unico momento en que se sabe que no hay ninguno en vuelo --se genera de
    uno en uno, y la fila arranca la siguiente solo cuando la anterior
    termino--. Llamarlo al pedir un bin barreria el archivo que otro bin
    esta escribiendo en ese instante, porque dos bins de la misma carpeta
    comparten carpeta de proxies.
    """
    try:
        pedazos = [p for p in carpeta.iterdir()
                   if p.is_file() and p.name.endswith(SUFIJO_PARCIAL)]
    except OSError:
        return 0   # la carpeta no esta, o no se puede leer: nada que barrer
    for pedazo in pedazos:
        pedazo.unlink(missing_ok=True)
    return len(pedazos)


class Interrumpido(RuntimeError):
    """Se corto a mitad de camino porque alguien lo pidio, no porque fallara."""


def generar(original: Path, carpeta: Path, ffmpeg: str | None = None,
            cancelado=None, latido: float = 0.25) -> Path:
    """Genera UN proxy y devuelve su ruta. Levanta si ffmpeg falla.

    Escribe a un nombre temporal y renombra al final. Sin eso, cancelar o
    quedarse sin disco a la mitad deja un `.mp4` truncado con el nombre
    bueno -- y la proxima corrida lo daria por hecho y lo engancharia. Un
    proxy a medias es peor que ninguno: se ve, y miente sobre donde termina
    el clip.

    `cancelado` es un invocable que se consulta cada `latido` segundos
    MIENTRAS ffmpeg corre. Sin el, esto era una llamada que no se podia
    interrumpir: al cerrar la app durante una tanda, la ventana se quedaba
    congelada hasta que terminara el clip en curso -- y con una toma de dron
    de tres minutos y medio eso son varios minutos mirando una app muerta.
    """
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = ruta_de_proxy(original, carpeta)
    parcial = destino.with_name(destino.name + SUFIJO_PARCIAL)
    proceso = subprocess.Popen(
        comando(original, parcial, ffmpeg),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    while True:
        try:
            _, error = proceso.communicate(timeout=latido)
            break
        except subprocess.TimeoutExpired:
            if cancelado is not None and cancelado():
                proceso.terminate()
                try:
                    proceso.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proceso.kill()
                parcial.unlink(missing_ok=True)
                raise Interrumpido(f"se canceló el proxy de {original.name}") from None
    if proceso.returncode != 0 or not parcial.exists():
        parcial.unlink(missing_ok=True)
        cola = (error or "").strip().splitlines()
        raise RuntimeError(
            f"ffmpeg no pudo generar el proxy de {original.name}: "
            + (cola[-1] if cola else f"código {proceso.returncode}")
        )
    parcial.replace(destino)
    return destino
