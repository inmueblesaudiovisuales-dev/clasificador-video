"""Los bins: de que camara/tarjeta salio cada clip.

Vive APARTE de `Clip` a proposito. `Clip.to_dict()` es el contrato con el
plugin de Premiere y no se toca -- mismo criterio que ya se uso con los
tamaños, las duraciones y las rotaciones, que viajan al lado en el autosave
en vez de meterse dentro del clip.

Este modulo solo conoce indices de clip y nombres. No sabe de Qt, no lee
disco y no decide como se ve nada.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# Carpetas a las que el origen de un bin NUNCA sube. Subir hasta aqui
# convertiria «señala la carpeta del bin» en «señala tu disco entero», y
# reencontrar el material tendria que recorrerlo completo.
RAICES_DEMASIADO_ARRIBA = frozenset({
    Path("/"), Path("/Users"), Path("/Volumes"), Path.home(),
})


def raiz_comun(actual: Path, nuevo: Path) -> Path:
    """La carpeta que cubre a las dos, o `actual` si no hay una razonable.

    Es LA definicion de «demasiado arriba» del repo: la usan el origen de un
    bin al crecer y el sitio del drop al decidir de que carpeta viene una
    tanda. Una sola, a proposito -- dos criterios distintos de hasta donde
    subir darian dos origenes distintos para el mismo material.
    """
    if actual == nuevo:
        return actual
    try:
        comun = Path(os.path.commonpath([str(actual), str(nuevo)]))
    except ValueError:
        return actual   # una absoluta y otra relativa: no hay ancestro
    if comun in RAICES_DEMASIADO_ARRIBA or len(comun.parts) <= 1:
        return actual
    return comun


def raiz_comun_de(carpetas: list[Path]) -> Path | None:
    """La carpeta que cubre a todas, o la primera si subir seria demasiado.

    `None` solo cuando no hay carpetas. Lo usa el sitio del drop, que es
    donde se sabe de que carpeta viene cada archivo: soltar material de dos
    carpetas a la vez tomaba la del primero, y el resto quedaba colgando de
    una carpeta que no lo contiene -- o sea, sin ruta relativa.
    """
    if not carpetas:
        return None
    raiz = carpetas[0]
    for otra in carpetas[1:]:
        raiz = raiz_comun(raiz, otra)
    return raiz


@dataclass
class Bin:
    nombre: str
    origen: Path
    clips: list[int] = field(default_factory=list)


class BinTree:
    def __init__(self) -> None:
        self._bins: list[Bin] = []

    def agregar(self, nombre: str, origen: Path, clips: list[int]) -> str:
        """Devuelve el nombre con el que quedo, que puede no ser el pedido."""
        nombre = self._nombre_libre(nombre.strip() or origen.name)
        self._bins.append(Bin(nombre=nombre, origen=origen, clips=list(clips)))
        return nombre

    def crear_vacio(self, nombre: str) -> str:
        """Un bin sin clips todavia.

        Existe porque el gesto que Bruno pidio es el de Premiere: creas el
        bin y luego le arrastras material. Nada lo poda cuando se queda sin
        clips -- si se podara, el bin desapareceria en el instante entre
        crearlo y soltarle el primer clip.
        """
        # `.strip() or "Bin"` aqui y no confiando en `agregar`: alla el
        # respaldo de un nombre en blanco es el nombre de la carpeta de
        # origen, y un bin creado vacio no tiene carpeta -- se quedaria sin
        # nombre. Es alcanzable en cuanto el boton «+ Bin nuevo» pase texto
        # del usuario.
        return self.agregar(nombre.strip() or "Bin", Path(""), [])

    def mover(self, indices: list[int], destino: str | None) -> None:
        """Cambia de bin a esos clips y NADA mas.

        No toca el indice de ningun clip, y por eso no hay que correr
        `_proxy_sizes`, `_clip_durations` ni el historial: mover entre bins
        es solo cambiar de lista quien esta en cual. Ese es el motivo de que
        esta operacion sea barata, y conviene que siga siendolo.

        `destino=None` los deja sueltos, que es un estado valido: caen en la
        seccion «Sin bin».
        """
        moviendo = set(indices)
        if not moviendo:
            return
        # Un destino que no existe NO puede tragarse los clips. Sin este
        # corte, el bucle de abajo los sacaba de todos lados y el de mas
        # abajo no encontraba a quien darselos: `mover([0], "Typo")`
        # terminaba siendo `mover([0], None)`. Con el arrastre conectado,
        # soltar sobre un encabezado recien renombrado te vaciaba el bin.
        if destino is not None and destino not in self.nombres():
            return
        for b in self._bins:
            if b.nombre != destino:
                b.clips = [i for i in b.clips if i not in moviendo]
        if destino is None:
            return
        for b in self._bins:
            if b.nombre == destino:
                # Los que llegan se AGREGAN al final, ordenados entre si --el
                # orden dentro del bin es el de rodaje, no el del arrastre--
                # pero sin reordenar a los que ya estaban: ese orden es dato
                # de quien lleno el bin, y de el vive la nocion de «el clip
                # anterior». `mover` cambia de bin y nada mas.
                ya = set(b.clips)
                b.clips = b.clips + sorted(i for i in moviendo if i not in ya)
                return

    def _nombre_libre(self, nombre: str) -> str:
        usados = self.nombres()
        if nombre not in usados:
            return nombre
        n = 2
        while f"{nombre} {n}" in usados:
            n += 1
        return f"{nombre} {n}"

    def nombres(self) -> list[str]:
        return [b.nombre for b in self._bins]

    def clips_de(self, nombre: str) -> list[int]:
        for b in self._bins:
            if b.nombre == nombre:
                return list(b.clips)
        return []

    def origen_de(self, nombre: str) -> Path | None:
        """La carpeta de la que salio el bin. El encabezado la escribe
        debajo del nombre, en mono y apagada, para responder «¿de que
        tarjeta salio esto?» sin cambiar de vista."""
        for b in self._bins:
            if b.nombre == nombre:
                return b.origen
        return None

    def mapa_por_clip(self) -> dict[int, str]:
        """De indice de clip a nombre de bin, de una sola pasada.

        Lo usa el filtro: preguntarle a `bin_de` clip por clip recorreria
        todos los bins una vez por clip, y eso es la cola de navegacion, que
        se recalcula en cada tecla.
        """
        return {i: b.nombre for b in self._bins for i in b.clips}

    def bin_de(self, indice: int) -> str | None:
        for b in self._bins:
            if indice in b.clips:
                return b.nombre
        return None

    def renombrar(self, nombre: str, nuevo: str) -> None:
        """Cambia el nombre SIN cambiar la posicion.

        Un nombre repetido se ignora en silencio, con el mismo criterio que
        `RoomSelection.rename`: es una entrada invalida del usuario, no un
        error del programa.
        """
        nuevo = nuevo.strip()
        if not nuevo or nuevo in self.nombres():
            return
        for b in self._bins:
            if b.nombre == nombre:
                b.nombre = nuevo
                return

    def sumar(self, nombre: str, clips: list[int],
              origen: Path | None = None) -> None:
        """Le agrega clips a un bin que ya existe, y AMPLIA su origen.

        Lo del origen no es un extra: el origen se fijaba una sola vez, al
        crear el bin, y este metodo no lo tocaba. Soltar la segunda tarjeta
        de la Sony sobre el bin que ya existe dejaba a esos clips sin ruta
        relativa --su archivo no cuelga del origen viejo-- y sin relativa no
        hay forma de reencontrarlos en otra computadora: saldrian como «no
        encontrados» aunque el archivo este ahi enfrente.

        `origen` es de donde viene el material nuevo, y es opcional: mover
        clips entre bins que ya existen no trae carpeta nueva.
        """
        for b in self._bins:
            if b.nombre == nombre:
                ya = set(b.clips)
                b.clips.extend(i for i in clips if i not in ya)
                if origen is not None:
                    b.origen = self._origen_ampliado(b.origen, origen)
                return

    @staticmethod
    def _origen_ampliado(actual: Path, nuevo: Path) -> Path:
        """El origen que cubre lo que el bin ya tenia Y lo que le llega.

        Solo puede subir: el origen tiene que seguir siendo ancestro de
        TODOS los clips del bin. Hasta donde, lo decide `raiz_comun`, que es
        la unica definicion de «demasiado arriba» del repo.
        """
        # Un bin creado con «+ Bin nuevo» nace con `Path("")`, que pathlib
        # normaliza a «.». Se trata aparte a proposito: sin este caso el
        # origen se quedaria en «.» para siempre --no hay ancestro comun
        # entre una relativa y una absoluta-- y ningun clip de ese bin
        # tendria ruta relativa.
        if str(actual) in ("", "."):
            return nuevo
        return raiz_comun(actual, nuevo)

    def quitar(self, nombre: str) -> list[int]:
        for i, b in enumerate(self._bins):
            if b.nombre == nombre:
                return self._bins.pop(i).clips
        return []

    def reindexar_tras_quitar(self, quitados: list[int]) -> None:
        """Corre los indices que quedan tras borrar `quitados` de la lista
        de clips.

        Es lo mas facil de romper de todo el modulo. Los bins guardan
        INDICES, no referencias al clip -- asi que borrar los clips 0 y 1
        no solo saca esos dos numeros de cada bin, tambien tiene que
        correr TODOS los indices mayores un lugar hacia atras: el que
        era 2 pasa a ser 0, porque en la lista de clips ya no hay nada
        antes de el. Restar solo la cuenta, sin quitar tambien los
        propios `quitados`, dejaria numeros que ya no corresponden a nada.
        """
        fuera = set(quitados)
        for b in self._bins:
            b.clips = [
                i - sum(1 for q in fuera if q < i)
                for i in b.clips
                if i not in fuera
            ]

    def to_list(self) -> list[dict]:
        return [
            {"nombre": b.nombre, "origen": self._origen_serializado(b),
             "clips": list(b.clips)}
            for b in self._bins
        ]

    @staticmethod
    def _origen_serializado(b: Bin) -> str:
        """`str(Path(""))` es «.», o sea «la carpeta actual» -- un origen
        que un bin creado vacio nunca tuvo. Se escribe cadena vacia, que
        es lo que `from_list` vuelve a leer como «sin origen»."""
        texto = str(b.origen)
        return "" if texto == "." else texto

    @classmethod
    def from_list(cls, datos: list[dict]) -> "BinTree":
        """Reconstruye desde lo que escribio `to_list()` -- o desde lo que
        haya en el autosave, que puede venir de una version distinta o de
        un archivo tocado a mano.

        Se blinda igual que `load_session` en autosave.py: lo que no se
        entiende se descarta en silencio, en vez de reventar
        `_restore_session` y dejar la app sin poder abrir. Un bin cuyos
        `clips` no se pueden leer como enteros se descarta entero -- es
        mas facil de razonar que adivinar cuales de sus indices salvar.
        """
        arbol = cls()
        if not isinstance(datos, list):
            return arbol
        for d in datos:
            if not isinstance(d, dict):
                continue
            try:
                clips = [int(i) for i in d.get("clips") or []]
            except (TypeError, ValueError):
                continue
            arbol._bins.append(
                Bin(
                    nombre=str(d.get("nombre") or ""),
                    origen=Path(str(d.get("origen") or "")),
                    clips=clips,
                )
            )
        return arbol

    @classmethod
    def desde_sesion(cls, datos: list[dict] | None, rutas: list[Path]) -> "BinTree":
        """Lo que se usa al restaurar.

        `datos` es `None` solo cuando la sesion es de antes de que
        existieran los bins: ahi se inventa un bin unico con todo el
        material, nombrado con la carpeta del primer clip. `[]` es
        distinto -- es que el usuario se quedo sin bins A PROPOSITO, por
        ejemplo borrando el ultimo -- y no dispara ese invento: hacerlo
        resucitaria justo lo que acaba de borrar.

        Despues de leer `datos`, los indices que ya no caben en `rutas`
        --sesion corrupta, o de un proyecto con menos clips que antes-- se
        descartan, y lo que quede sin bin se QUEDA sin bin: la hoja lo
        dibuja en su seccion de sueltos, que es solo una vista. Ver
        `_acotar_a`.
        """
        if datos is not None:
            arbol = cls.from_list(datos)
            arbol._acotar_a(len(rutas))
            return arbol
        arbol = cls()
        if rutas:
            arbol.agregar(rutas[0].parent.name, rutas[0].parent,
                          list(range(len(rutas))))
        return arbol

    def _acotar_a(self, total_clips: int) -> None:
        """Descarta los indices que ya no caben --sesion corrupta, o de un
        proyecto con menos clips que antes.

        Lo que queda sin bin se queda sin bin. Antes se le inventaba aqui
        un bin real llamado «Sin bin»; no se hace mas, por dos razones. La
        hoja usa esa misma cadena como titulo de su seccion de sueltos, asi
        que un bin con ese nombre haria salir el encabezado dos veces. Y
        «clip suelto» es un estado valido (§6.b del spec), no una anomalia
        que haya que normalizar al reabrir: se representa por AUSENCIA de
        bin, que es lo que `bin_de` ya devuelve como `None`.
        """
        for b in self._bins:
            b.clips = [i for i in b.clips if 0 <= i < total_clips]
