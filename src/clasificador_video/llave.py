"""La llave de la API: se pega una vez y se queda guardada.

DÓNDE SE GUARDA: en `~/.clasificador_video/`, junto a los recientes. Los
tres lugares que se descartaron, cada uno por su motivo:
  - el proyecto de Premiere -> viaja al cliente cuando Bruno le manda el
    proyecto;
  - junto al material -> se copia a discos y se sube a la nube con el
    shooting;
  - el repo -> se sube a GitHub, que es público.

Y NUNCA se imprime ni se escribe en ningún log. El log es el archivo que uno
manda cuando algo falla, o sea el que más ojos ve: una llave ahí dentro es
una llave regalada. Para depurar está `tapada`.

Sin Qt.
"""
from __future__ import annotations

import json
from pathlib import Path

RUTA = Path.home() / ".clasificador_video" / "llave.json"


def _destino(ruta: Path | None) -> Path:
    return RUTA if ruta is None else ruta


def guardar(valor: str, ruta: Path | None = None) -> None:
    destino = _destino(ruta)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps({"llave": str(valor or "").strip()}), encoding="utf-8"
    )


def leer(ruta: Path | None = None) -> str:
    """"" cuando no hay llave guardada, o cuando el archivo está roto.

    Que no haya es el caso de la primera vez, no un error: la pantalla pide
    que la peguen y sigue su vida. Y un archivo corrupto se trata igual, con
    el mismo criterio que `recientes`: cambiar una comodidad por un ladrillo
    sería un mal negocio.
    """
    try:
        datos = json.loads(_destino(ruta).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return ""
    if not isinstance(datos, dict):
        return ""
    return str(datos.get("llave") or "")


def borrar(ruta: Path | None = None) -> None:
    _destino(ruta).unlink(missing_ok=True)


def tapada(valor: str) -> str:
    """Cómo se enseña en pantalla: los últimos cuatro y lo demás tapado.

    Una llave de menos de ocho se tapa ENTERA. Enseñar los últimos cuatro de
    una llave corta es enseñar media llave.
    """
    texto = str(valor or "")
    if not texto:
        return ""
    if len(texto) < 8:
        return "••••••••"
    return "••••••••" + texto[-4:]
