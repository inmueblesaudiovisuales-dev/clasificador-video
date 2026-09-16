"""Elección del formato que viajará en el JSON hacia Premiere."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from clasificador_video.ui import theme


class _FilaFormato(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.radio: QRadioButton | None = None
        self.setCursor(Qt.PointingHandCursor)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self.radio is not None:
            self.radio.setChecked(True)
        super().mouseReleaseEvent(event)


class DialogoFormatoSecuencia(QDialog):
    """Una elección explícita; 1080p se agrega sin pedir una segunda decisión."""

    def __init__(self, sugerido: str | None, parent=None):
        super().__init__(parent)
        self.setObjectName("dialogoFormato")
        self.setWindowTitle("Secuencias para Premiere")
        self.setMinimumWidth(490)
        self._radios: dict[str, QRadioButton] = {}
        self._grupo = QButtonGroup(self)
        self._grupo.setExclusive(True)

        contenido = QVBoxLayout(self)
        contenido.setContentsMargins(28, 25, 28, 24)
        contenido.setSpacing(0)

        titulo = QLabel("Elige el formato principal", self)
        titulo.setObjectName("tituloFormato")
        contenido.addWidget(titulo)

        explicacion = QLabel(
            "Hay material vertical 2.7K. Elige entre las dos opciones verticales."
            if sugerido is None else
            f"Según tu material, sugerimos «{sugerido}». Puedes cambiarlo.", self
        )
        explicacion.setObjectName("explicacionFormato")
        explicacion.setWordWrap(True)
        contenido.addSpacing(8)
        contenido.addWidget(explicacion)
        contenido.addSpacing(22)

        self._seccion(contenido, "Vertical")
        self._opcion(contenido, "4K 9:16", "2160 × 3840  ·  59.94 fps", sugerido)
        self._opcion(contenido, "2.7K 9:16", "2160 × 3840  ·  59.94 fps", sugerido)
        contenido.addSpacing(18)
        self._seccion(contenido, "Horizontal")
        self._opcion(contenido, "4K 16:9", "3840 × 2160  ·  59.94 fps", sugerido)

        nota = QLabel(
            "Premiere creará dos secuencias vacías: esta y otra 1080p "
            "con el mismo encuadre.", self
        )
        nota.setObjectName("notaFormato")
        nota.setWordWrap(True)
        contenido.addSpacing(20)
        contenido.addWidget(nota)
        contenido.addSpacing(24)

        acciones = QHBoxLayout()
        acciones.setSpacing(10)
        acciones.addStretch()
        cancelar = QPushButton("Cancelar", self)
        cancelar.setObjectName("cancelarFormato")
        cancelar.clicked.connect(self.reject)
        acciones.addWidget(cancelar)
        self._exportar = QPushButton("Exportar JSON", self)
        self._exportar.setObjectName("exportarFormato")
        self._exportar.setEnabled(False)
        self._exportar.setDefault(True)
        self._exportar.clicked.connect(self.accept)
        acciones.addWidget(self._exportar)
        contenido.addLayout(acciones)

        self.setStyleSheet(f"""
            QDialog#dialogoFormato {{ background: {theme.BG_SURFACE_0}; color: {theme.TEXT}; }}
            QLabel {{ color: {theme.TEXT}; background: transparent; }}
            QLabel#tituloFormato {{ font-size: 20px; font-weight: 700; }}
            QLabel#explicacionFormato {{ font-size: 13px; color: {theme.TEXT_2}; }}
            QLabel#seccionFormato {{ font-size: 12px; font-weight: 600; color: {theme.TEXT_2}; }}
            QLabel#detalleFormato {{ font-size: 12px; color: {theme.TEXT_2}; }}
            QLabel#notaFormato {{ font-size: 12px; color: {theme.TEXT_2}; }}
            QLabel#sugeridoFormato {{ font-size: 11px; font-weight: 600;
                color: {theme.CURRENT_COLOR}; }}
            QFrame#filaFormato {{ background: {theme.BG_SURFACE_1};
                border: 1px solid {theme.LINE}; border-radius: 7px; }}
            QFrame#filaFormato[seleccionada="true"] {{
                background: {theme.BG_SURFACE_2}; border-color: {theme.CURRENT_COLOR}; }}
            QRadioButton {{ color: {theme.TEXT}; font-size: 15px; font-weight: 600;
                background: transparent; spacing: 10px; }}
            QRadioButton::indicator {{ width: 15px; height: 15px;
                border: 1px solid {theme.TEXT_3}; border-radius: 8px;
                background: {theme.BG_SURFACE_0}; }}
            QRadioButton::indicator:checked {{ border-color: {theme.CURRENT_COLOR};
                background: {theme.CURRENT_COLOR}; }}
            QPushButton {{ background: {theme.BG_SURFACE_2}; color: {theme.TEXT};
                border: 1px solid {theme.LINE}; border-radius: 6px;
                padding: 9px 16px; font-size: 13px; }}
            QPushButton#exportarFormato:enabled {{ background: {theme.CURRENT_COLOR};
                color: {theme.BG_APP}; border-color: {theme.CURRENT_COLOR};
                font-weight: 700; }}
            QPushButton#exportarFormato:disabled {{ color: {theme.TEXT_3}; }}
            QPushButton:focus {{ border-color: {theme.CURRENT_COLOR}; }}
        """)

        if sugerido in self._radios:
            self._radios[sugerido].setChecked(True)

    @property
    def formato_elegido(self) -> str | None:
        return next((formato for formato, radio in self._radios.items()
                     if radio.isChecked()), None)

    def accept(self) -> None:
        if self.formato_elegido is not None:
            super().accept()

    def _seccion(self, contenido: QVBoxLayout, texto: str) -> None:
        etiqueta = QLabel(texto, self)
        etiqueta.setObjectName("seccionFormato")
        contenido.addWidget(etiqueta)
        contenido.addSpacing(8)

    def _opcion(self, contenido: QVBoxLayout, formato: str,
                detalles: str, sugerido: str | None) -> None:
        fila = _FilaFormato(self)
        fila.setObjectName("filaFormato")
        fila.setProperty("seleccionada", "false")
        disposicion = QHBoxLayout(fila)
        disposicion.setContentsMargins(15, 11, 15, 11)
        disposicion.setSpacing(10)
        textos = QVBoxLayout()
        textos.setSpacing(3)
        radio = QRadioButton(formato, fila)
        fila.radio = radio
        self._grupo.addButton(radio)
        self._radios[formato] = radio
        textos.addWidget(radio)
        detalle = QLabel(detalles, fila)
        detalle.setObjectName("detalleFormato")
        detalle.setAttribute(Qt.WA_TransparentForMouseEvents)
        textos.addWidget(detalle)
        disposicion.addLayout(textos)
        disposicion.addStretch()
        if formato == sugerido:
            marca = QLabel("Sugerido", fila)
            marca.setObjectName("sugeridoFormato")
            marca.setAlignment(Qt.AlignTop | Qt.AlignRight)
            marca.setAttribute(Qt.WA_TransparentForMouseEvents)
            disposicion.addWidget(marca)
        radio.toggled.connect(lambda activo, cuadro=fila: self._seleccion(cuadro, activo))
        contenido.addWidget(fila)
        contenido.addSpacing(8)

    def _seleccion(self, fila: QFrame, activa: bool) -> None:
        fila.setProperty("seleccionada", "true" if activa else "false")
        fila.style().unpolish(fila)
        fila.style().polish(fila)
        self._exportar.setEnabled(self.formato_elegido is not None)
