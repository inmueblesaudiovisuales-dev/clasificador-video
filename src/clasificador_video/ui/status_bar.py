# src/clasificador_video/ui/status_bar.py
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from clasificador_video.probe import orientacion_de
from clasificador_video.ui import theme


class StatusBar(QWidget):
    """Barra inferior de 24 px: los datos que se CONSULTAN, no los que se
    persiguen.

    Aca van resolucion, fps, orientacion y ruta del volumen -- informacion
    de referencia que en el diseño viejo ocupaba un panel de 200 px al
    costado del video.
    """

    unclassified_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("statusBar")
        self.setFixedHeight(theme.STATUSBAR_HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(13, 0, 13, 0)
        layout.setSpacing(15)

        self.clip_label = QLabel("")
        self.clip_label.setObjectName("statusMono")
        # es un BOTON, no una etiqueta: DECISIONES.md lo llama «literalmente
        # el boton de segui trabajando» -- clickearlo filtra por lo que falta
        self.unclassified_label = QPushButton("")
        self.unclassified_label.setObjectName("unclassifiedBadge")
        self.unclassified_label.setFlat(True)
        self.unclassified_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.unclassified_label.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.unclassified_label.hide()
        self.unclassified_label.clicked.connect(self.unclassified_clicked.emit)
        # va del lado derecho, PEGADO a la ruta del volumen y antes que
        # ella, como en el mockup (`proxies 1080p · 128/128` y luego
        # `/Volumes/FX30/CasaLomas · 214 GB`): es informacion de
        # referencia sobre el material, la misma familia que la ruta.
        self.proxy_label = QLabel("")
        self.proxy_label.setObjectName("statusMono")
        self.proxy_label.hide()
        self.volume_label = QLabel("")
        self.volume_label.setObjectName("statusMono")

        layout.addWidget(self.clip_label)
        layout.addWidget(self.unclassified_label)
        layout.addStretch(1)
        layout.addWidget(self.proxy_label)
        layout.addWidget(self.volume_label)

    def set_clip_info(
        self,
        nombre: str | None,
        tamano: tuple[int, int] | None,
        fps: float | None,
        rotacion: int | None,
    ) -> None:
        if not nombre:
            self.clip_label.setText("")
            return
        # se muestra lo que se sabe: en una sesion restaurada de disco no se
        # volvio a correr ffprobe y no hay tamaño, pero el nombre del archivo
        # tiene que verse igual.
        partes = [nombre]
        if tamano:
            ancho, alto = tamano
            partes.append(f"{ancho}×{alto}")
        if fps:
            partes.append(f"{fps:.2f} fps")
        if tamano:
            ancho, alto = tamano
            # la MISMA funcion que decide la orientacion del manifest: si
            # la barra dice «vertical» y el manifest declara «horizontal»,
            # una de las dos miente y nadie se entera hasta Premiere.
            orientacion = orientacion_de(ancho, alto)
            partes.append(
                f"{orientacion} (rot {rotacion}°)" if rotacion else orientacion
            )
        self.clip_label.setText(" · ".join(partes))

    def set_resumen(self, clips: int, verticales: int, horizontales: int) -> None:
        """Lo que va en el lugar del clip actual cuando estas en la hoja:
        `128 clips · 74 verticales · 54 horizontales`, como el mockup.

        Sin un clip en pantalla, «resolucion, fps y orientacion del clip
        actual» no viene al caso -- pero la forma del shooting entero si,
        porque es lo que decide la orientacion de la secuencia en Premiere.

        Sin tamaños conocidos (sesion restaurada, sin volver a correr
        ffprobe) va solo `128 clips`: un `0 verticales · 0 horizontales`
        seria una respuesta falsa a una pregunta que no se puede contestar.
        """
        if not clips:
            self.clip_label.setText("")
            return
        partes = [f"{clips} clips"]
        if verticales or horizontales:
            partes.append(f"{verticales} verticales")
            partes.append(f"{horizontales} horizontales")
        self.clip_label.setText(" · ".join(partes))

    def set_unclassified(self, cuantos: int) -> None:
        self.unclassified_label.setText(
            f"⚠ {cuantos} sin clasificar — click para filtrarlos" if cuantos else ""
        )
        self.unclassified_label.setVisible(bool(cuantos))

    def set_proxies(self, cuantos: int, total: int, resolucion: str) -> None:
        """`proxies 720p · 118/128`, o nada si no hay ni uno.

        Sin proxies el contador se esconde en vez de mostrar `· 0/128`:
        seria ruido fijo en cada sesion de dron. Y si los proxies conocidos
        no miden todos lo mismo --dos camaras con perfiles distintos-- se
        cae la palabra de resolucion y queda `proxies · 118/128`. Mejor
        callar que decir una resolucion que no es la de todos.
        """
        if not cuantos or not total:
            self.proxy_label.hide()
            return
        etiqueta = f"proxies {resolucion} · " if resolucion else "proxies · "
        self.proxy_label.setText(f"{etiqueta}{cuantos}/{total}")
        self.proxy_label.show()

    def set_volume(self, ruta: str, gigabytes: int | None = None) -> None:
        """`/Volumes/FX30/CasaLomas · 214 GB`, como el mockup.

        Sin tamaño va solo la ruta: pasa con un volumen de red o con una
        carpeta que ya no esta montada, y un `0 GB` inventado se leeria
        como disco lleno.
        """
        self.volume_label.setText(f"{ruta} · {gigabytes} GB" if gigabytes else ruta)
