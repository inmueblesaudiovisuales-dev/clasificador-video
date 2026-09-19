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

import os
import re
import subprocess
from pathlib import Path

from clasificador_video.binarios import ruta_de

# Los proxies generados terminan igual que los de la Sony. No es cosmetica:
# `ingest.es_archivo_de_proxy` descarta por ese sufijo, asi que si algun dia
# alguien arrastra la carpeta de proxies como si fuera material, no entra
# nada duplicado.
SUFIJO = "S03"

CARPETA = "Proxies"

# El nombre por omision de la carpeta de proxies. Se usa en dos papeles
# distintos: `carpeta_al_lado` --donde vivian hasta el 2026-08-22, que se
# sigue mirando al buscar-- y `carpeta_por_defecto`, que es lo que se le
# PROPONE a Bruno cuando no hay una carpeta suya que reconocer.
#
# Desde el 2026-08-25 los nuevos van a la carpeta que el elige, en una
# subcarpeta por material. Ver
# `specs/2026-08-25-carpeta-de-proxies-elegible-design.md`.


def carpeta_de_proxies(carpeta_del_bin: Path) -> Path:
    """ADENTRO de la carpeta del material. Donde van los proxies nuevos.

    Cambio del 2026-08-22, y revierte a proposito la decision del 10 de
    agosto --«al lado, porque adentro ensuciaria la copia de la tarjeta»--.
    La razon nueva de Bruno: adentro los proxies **viajan con el material**
    cuando mueve o copia la carpeta a otro disco, en vez de quedarse
    huerfanos al lado. El costo que acepto, escrito: la copia de respaldo de
    la tarjeta ahora pesa mas.

    Meter la carpeta adentro NO hace que se reimporten como clips: el ingest
    toma solo los archivos directos de una carpeta y no baja a las
    subcarpetas (ver `ingest.encontrar_videos`). Comprobado antes del cambio;
    era el riesgo grande y no existe.
    """
    return carpeta_del_bin / CARPETA


def carpeta_al_lado(carpeta_del_bin: Path) -> Path:
    """Donde vivian los proxies ANTES del 2026-08-22.

    Existe solo para seguir encontrando los de los proyectos de antes. No se
    escribe aqui salvo que adentro no se pueda (ver `carpeta_para_escribir`).
    """
    return carpeta_del_bin.parent / CARPETA


_NUMERO = re.compile(r"^(\d+)\.\s")


def _numero_de(nombre: str) -> str | None:
    """El prefijo `NN.` de un nombre de carpeta, o `None` si no lo trae."""
    m = _NUMERO.match(nombre)
    return m.group(1) if m else None


def subcarpeta_por_numero(elegida: Path, carpeta_del_bin: Path) -> Path:
    """Como `subcarpeta_del_bin`, pero reconoce una carpeta YA HECHA por
    Bruno aunque el nombre no sea idéntico -- basta que el número
    coincida (spec 2026-09-18 §3).

    Bruno trae de fábrica `02. PROXY DRONE` como hermana de
    `02. VIDEO DRONE`: mismo número, nombre distinto a propósito. La
    regla de agosto --nombre IDÉNTICO-- la ignoraba y creaba
    `02. VIDEO DRONE` DENTRO de la carpeta de proxies, dejando la suya
    vacía. Aquí el número manda: si hay alguna subcarpeta de `elegida`
    cuyo número coincide, se usa esa. Sin número que comparar, o sin
    coincidencia, se cae al nombre de siempre (comportamiento de agosto,
    sin cambio).
    """
    numero = _numero_de(carpeta_del_bin.name)
    if numero is not None:
        try:
            for hija in elegida.iterdir():
                if hija.is_dir() and _numero_de(hija.name) == numero:
                    return hija
        except OSError:
            pass  # la carpeta elegida puede no existir todavía
    return elegida / carpeta_del_bin.name


def carpeta_por_defecto(carpeta_del_bin: Path) -> Path:
    """La que se PROPONE cuando no hay una carpeta de proxies que reconocer.

    Es la misma ruta que `carpeta_al_lado`, pero se usa para otra cosa y por
    eso tiene nombre propio: aquella dice donde BUSCAR lo viejo, esta dice
    que ofrecerle a Bruno para lo nuevo. Los archivos nuevos van un nivel mas
    abajo, en la subcarpeta del bin.
    """
    return carpeta_del_bin.parent / CARPETA


def proponer_carpeta(carpeta_del_bin: Path) -> Path:
    """Que carpeta ofrecerle a Bruno, para que la pregunta llegue contestada.

    Un explorador de archivos en blanco no es una opcion opcional: es tarea.
    Asi que se mira si al lado del material ya hay una carpeta de proxies
    SUYA y se propone esa, con la ruta a la vista.

    `Proxies/` --la de `carpeta_por_defecto`-- queda fuera de los candidatos a
    proposito: no es una convencion de Bruno, es donde la propia app tiraba
    los archivos hasta hoy. En su proyecto real conviven las dos, y sin esta
    exclusion serian dos candidatas, no habria forma de elegir, y se
    propondria justo la que el no queria.

    Con varias candidatas NO se adivina: se propone la de siempre. Esto
    nunca escribe nada -- solo elige que enseñar.
    """
    padre = carpeta_del_bin.parent
    defecto = carpeta_por_defecto(carpeta_del_bin)
    try:
        candidatas = [d for d in padre.iterdir()
                      if d.is_dir() and "prox" in d.name.lower()
                      and d != carpeta_del_bin and d != defecto]
    except OSError:
        # el disco del material puede no estar montado; proponer algo es
        # mejor que reventar la pregunta entera
        candidatas = []
    return candidatas[0] if len(candidatas) == 1 else defecto


def carpetas_de_proxies(carpeta_del_bin: Path,
                        elegida: Path | None = None) -> list[Path]:
    """Donde buscar, EN ORDEN: la elegida, adentro, al lado.

    Los tres lugares se miran siempre, y por eso elegir una carpeta nueva no
    invalida ni un archivo de los que ya existen. Bruno lo pidio explicito el
    2026-08-25: a los proyectos que ya tiene, no se les mueve nada.

    `elegida is None` es un proyecto que nunca contesto la pregunta, y ahi la
    lista es exactamente la de antes.
    """
    lugares = []
    if elegida is not None:
        lugares.append(subcarpeta_por_numero(elegida, carpeta_del_bin))
    lugares.append(carpeta_de_proxies(carpeta_del_bin))
    lugares.append(carpeta_al_lado(carpeta_del_bin))
    return lugares


def ruta_de_proxy_existente(original: Path, carpeta_del_bin: Path,
                            elegida: Path | None = None) -> Path | None:
    """El proxy de ese clip, este donde este de los tres lugares. `None` si
    no hay.

    Es lo que hace retrocompatibles los DOS cambios de sitio: un proyecto de
    antes abre igual, sin regenerar nada y sin mover un archivo.
    """
    for carpeta in carpetas_de_proxies(carpeta_del_bin, elegida):
        candidato = ruta_de_proxy(original, carpeta)
        if candidato.exists():
            return candidato
    return None


def _se_puede_escribir(elegida: Path) -> bool:
    """Si se puede llenar la carpeta elegida, o crearla donde Bruno la puso.

    Mira la carpeta elegida y, si todavia no existe, a su padre -- **un solo
    nivel, no la cadena entera**. La diferencia importa: subir hasta el
    primer antepasado que exista haria que `/Volumes/SSD/Proxies` con el SSD
    desconectado pareciera escribible, porque `/Volumes` existe, y la app
    inventaria un arbol de carpetas donde deberia estar el disco. Un nivel
    alcanza para el caso real --aceptar la carpeta propuesta, que todavia no
    existe-- y no alcanza para inventar un disco.
    """
    if elegida.exists():
        return elegida.is_dir() and os.access(elegida, os.W_OK)
    padre = elegida.parent
    return padre.is_dir() and os.access(padre, os.W_OK)


def carpeta_para_escribir(carpeta_del_bin: Path,
                          elegida: Path | None = None) -> Path:
    """La subcarpeta de la elegida si se puede; si no, adentro; si no, al lado.

    El material puede estar en una tarjeta protegida contra escritura, o
    llena, y la carpeta elegida puede estar en un disco que hoy no esta
    conectado. Quedarse sin proxies por eso seria peor que ponerlos donde
    funcionaban ayer.
    """
    if elegida is not None:
        destino = subcarpeta_por_numero(elegida, carpeta_del_bin)
        if destino.exists() or _se_puede_escribir(elegida):
            return destino
    adentro = carpeta_de_proxies(carpeta_del_bin)
    if adentro.exists():
        return adentro
    if os.access(carpeta_del_bin, os.W_OK):
        return adentro
    return carpeta_al_lado(carpeta_del_bin)


def ruta_de_proxy(original: Path, carpeta: Path) -> Path:
    """Siempre `.mp4`, sea cual sea la extension del original: el proxy lo
    escribimos nosotros y lo escribimos en un solo formato."""
    return carpeta / f"{original.stem}{SUFIJO}.mp4"


def comando(original: Path, destino: Path, ffmpeg: str | None = None) -> list[str]:
    """El comando de ffmpeg, armado aparte para poder probarlo sin correrlo.

    Ya NO escala (spec 2026-09-18 §2): el proxy sale exactamente al tamaño
    del original. El peso lo decide el bitrate (`-b:v 6M`), no la
    resolución -- medido: un proxy de 4K real pesa lo mismo que uno de
    720p con el mismo bitrate.

    El unico detalle que sigue costando caro es `-map 0:v:0`: los MP4 del
    dron traen una miniatura JPEG incrustada como SEGUNDA pista de video, y
    sin esto ffmpeg elige esa por ser la de mejor "calidad".
    """
    return [
        ffmpeg or str(ruta_de("ffmpeg")),
        "-y",                       # el destino ya se comprobo antes de llamar
        "-i", str(original),
        "-map", "0:v:0",            # el video de verdad, no la miniatura
        "-map", "0:a?",             # el audio si lo hay, y sin fallar si no
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
