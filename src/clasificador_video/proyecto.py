"""El proyecto como documento: lo que se guarda y lo que se lee.

Hasta ahora esto vivia repartido entre `MainWindow._write_autosave_now` y
`app._restore_session`, y el archivo era uno solo y escondido. Aqui esta la
MISMA forma, con nombre propio y con una cosa mas: la ruta de cada clip
**relativa a la carpeta de su bin**, que es lo unico que permite reencontrar
el material en otra computadora -- las absolutas nunca coinciden ahi.

Sin Qt: esto se prueba sin abrir una ventana.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

VERSION = 1
EXTENSION = ".cvproj"


def rutas_relativas(clips: list, bins) -> dict[int, str]:
    """Por cada clip, su ruta respecto a la carpeta de su bin.

    Los que no tienen bin, o cuyo archivo esta fuera de la carpeta de su
    bin, quedan fuera: inventarles una relativa con `..` seria una ruta
    fragil que al reencontrar apuntaria a cualquier lado.
    """
    relativas: dict[int, str] = {}
    for indice, clip in enumerate(clips):
        nombre = bins.bin_de(indice)
        if nombre is None:
            continue
        origen = bins.origen_de(nombre)
        # Un bin creado vacio tiene `Path("")`, que pathlib normaliza a «.»
        # -- NO a `None`. Se descarta a proposito y no de casualidad (que es
        # lo que pasaba: `relative_to(".")` truena con una ruta absoluta).
        if origen is None or str(origen) in ("", "."):
            continue
        try:
            relativa = Path(clip.ruta).relative_to(origen)
        except ValueError:
            continue  # el archivo no cuelga de la carpeta de su bin
        # `relative_to` es puramente lexico: si la ruta del clip trae un
        # `..`, devuelve una relativa que se sale de la carpeta. Al
        # reencontrar eso se usa como `carpeta / relativa`, o sea que
        # apuntaria fuera de lo que Bruno señalo.
        if ".." in relativa.parts:
            continue
        relativas[indice] = str(relativa)
    return relativas


def por_indice_de_clip(mapa: dict | None) -> dict[int, object]:
    """Las llaves del JSON son texto; adentro de la app son enteros.

    Sin este puente, un `{"0": 700}` recien leido del archivo y un `{0: ...}`
    de memoria no se cruzan nunca, y el dato se pierde **en silencio** --que
    es la forma en que este modulo hace daño.
    """
    normalizado: dict[int, object] = {}
    for llave, valor in (mapa or {}).items():
        try:
            normalizado[int(llave)] = valor
        except (TypeError, ValueError):
            continue
    return normalizado


def _pesos_validos(mapa: dict | None) -> dict[int, int]:
    """Solo lo que de verdad es un peso. `True` es un `int` para Python y no
    es un peso: colarlo dejaria un `bytes` con el que nada puede calzar."""
    return {i: v for i, v in por_indice_de_clip(mapa).items()
            if isinstance(v, int) and not isinstance(v, bool)}


def con_pesos_medidos(data: dict, previos: dict | None = None) -> dict:
    """El documento con el peso real de cada archivo, medido del disco.

    **Esto toca disco, asi que corre en el hilo del guardado y no en el de la
    interfaz.** Un `stat` cuesta menos de un milisegundo en local, pero sobre
    un volumen montado e incomunicado se traba hasta el timeout, y son uno
    por clip en serie: con 109 clips la app se congela. Sacar la escritura de
    ese hilo fue justo lo que arreglo el lag al clasificar rapido, y medir
    ahi seria volver a meterlo.

    El peso de cada archivo es lo unico con que se puede confirmar que un
    archivo reencontrado es el que era: el nombre lo repiten las camaras y la
    duracion sola no distingue dos tomas iguales.

    Se combinan tres fuentes, en este orden: lo que ya estaba en el archivo
    (`previos`), lo que trae el documento, y lo que se pudo medir ahora. Lo
    que no se puede medir **conserva** lo de antes en vez de borrarse -- ese
    borrado, que pasaba solo a los pocos segundos de abrir el proyecto sin la
    media, dejaba a Bruno sin con que confirmar nada.
    """
    pesos = _pesos_validos(previos)
    pesos.update(_pesos_validos(data.get("bytes")))
    for indice, clip in enumerate(data.get("clips") or []):
        try:
            pesos[indice] = Path(str(clip["ruta"])).stat().st_size
        except (OSError, KeyError, TypeError):
            # guardar tiene que funcionar con el disco desconectado, o se
            # pierde trabajo justo cuando mas duele
            continue
    # una copia: el que llama sigue siendo dueño del suyo
    return {**data, "bytes": {str(i): t for i, t in sorted(pesos.items())}}


def _relativas_con_respaldo(clips: list, bins,
                            conocidas: dict | None) -> dict[int, str]:
    """Las relativas que se pueden calcular, mas las que ya se sabian.

    Calcular gana siempre: describe donde esta el archivo AHORA. Pero lo que
    no se puede calcular no se tira, y eso importa justo al reconectar a
    medias: el bin pasa a colgar de la carpeta nueva y el clip que sigue
    perdido apunta a la vieja, asi que `relative_to` falla y su relativa
    desapareceria del documento -- dejandolo sin con que reencontrarse
    nunca mas. Es la unica pieza que no se puede volver a deducir cuando el
    archivo no esta en disco.
    """
    respaldo = {i: str(r) for i, r in por_indice_de_clip(conocidas).items()}
    respaldo.update(rutas_relativas(clips, bins))
    # un clip que ya no existe no deja rastro: el respaldo puede venir de un
    # proyecto con mas clips de los que hay ahora.
    return {i: r for i, r in sorted(respaldo.items()) if 0 <= i < len(clips)}


def a_dict(proyecto: str, rooms: list[str], clips: list, bins,
           tamanos: dict, duraciones: dict, rotaciones: dict,
           bytes_conocidos: dict | None = None,
           relativas_conocidas: dict | None = None,
           agrupar_por_cuarto: bool = True,
           modo_horizontal: bool = False) -> dict:
    """La forma del documento. **Puro: no toca disco.**

    Los pesos que salen de aqui son los que ya se sabian (`bytes_conocidos`,
    tal cual vienen de `abrir`). Medirlos de verdad es trabajo de
    `con_pesos_medidos`, que corre donde el disco no estorba.
    """
    return {
        "version": VERSION,
        "proyecto": proyecto,
        "rooms": list(rooms),
        "clips": [c.to_dict() for c in clips],
        # Todo esto va AL LADO de los clips y no adentro: `Clip.to_dict()`
        # es el contrato con el plugin de Premiere y no se toca.
        "tamanos": {str(i): [a, h] for i, (a, h) in tamanos.items()},
        "duraciones": {str(i): s for i, s in duraciones.items()},
        "rotaciones": {str(i): r for i, r in rotaciones.items()},
        "bins": bins.to_list(),
        "relativas": {
            str(i): r for i, r in
            _relativas_con_respaldo(clips, bins, relativas_conocidas).items()
        },
        # El peso en bytes es lo unico con que se puede confirmar que un
        # archivo reencontrado es el que era: el nombre lo repiten las
        # camaras y la duracion sola no distingue dos tomas iguales.
        "bytes": {str(i): t
                  for i, t in sorted(_pesos_validos(bytes_conocidos).items())},
        # Como se ve la hoja: agrupada por cuarto, o en orden de rodaje. Es
        # lo unico de VISTA que se guarda, y se guarda porque cambiarlo en
        # cada sesion seria un paso previo antes de trabajar --justo lo que
        # este proyecto no quiere-- y porque la respuesta depende del
        # shooting, no del dia.
        "agrupar_por_cuarto": bool(agrupar_por_cuarto),
        # Y si el visor va ancho --la hoja escondida en modo clip--, que
        # depende de si el shooting es del dron o de la Sony. Apagado por
        # omision: es como se comportaba antes de que existiera.
        "modo_horizontal": bool(modo_horizontal),
    }


def guardar(ruta: Path, data: dict) -> None:
    """Escritura atomica: temporal + rename.

    El UNICO escritor del documento. Hubo dos --este y `save_session`-- y era
    un cuidado que habia que acordarse de aplicar en los dos lados: el que
    escribia el archivo de Bruno el 99% del tiempo era justo el que NO
    limpiaba su temporal si fallaba, y eso dejaba un `Casa Lomas.cvproj.tmp`
    al lado del proyecto que nadie sabe que es.
    """
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_suffix(ruta.suffix + ".tmp")
    try:
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        os.replace(tmp, ruta)
    finally:
        # Si la escritura falla a medias --el disco lleno es el caso real--
        # el temporal quedaba a la vista en la carpeta de Bruno, como un
        # `Casa Lomas.cvproj.tmp` que nadie sabe que es. Tras el `replace`
        # ya no existe, y por eso el `missing_ok`.
        tmp.unlink(missing_ok=True)


def es_proyecto(data: dict | None) -> bool:
    """¿Este JSON es un proyecto de la app, o un archivo de otra cosa?

    `abrir` acepta cualquier JSON que sea un objeto, asi que con «Abrir
    otro…» se puede elegir un `.json` cualquiera. Sin esta pregunta, ese
    archivo abriria un «proyecto» vacio sin decir que no lo era, y Bruno
    veria una ventana en blanco donde creia tener su trabajo.

    Basta con UNA de las dos llaves: los proyectos convertidos de la sesion
    vieja pueden no traer `version`, y exigir las dos dejaria a Bruno sin
    poder abrir lo suyo.
    """
    if not isinstance(data, dict):
        return False
    return "version" in data or "clips" in data


def abrir(ruta: Path) -> dict | None:
    """`None` si no se pudo leer. Esto corre al elegir un archivo, asi que
    reventar aqui dejaria a Bruno sin forma de salir."""
    try:
        data = json.loads(ruta.read_text())
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    return data if isinstance(data, dict) else None
