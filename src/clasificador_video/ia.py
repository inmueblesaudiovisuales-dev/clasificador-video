"""La llamada a la API, y nada más.

Chiquito a propósito: no arma el cuerpo y no interpreta la respuesta --las
dos cosas viven en `guia.py`, que se prueba sin red--. Ese corte es lo que
deja cambiar de proveedor en un renglón: DeepSeek habla la misma API que
OpenAI, así que mudarse es esta URL.

Cada caso feo tiene su mensaje propio y **en palabras de Bruno** --«la llave
no sirve» y no «HTTP 401»--, y ninguno lleva la llave adentro: ese texto
termina en pantalla y la pantalla termina en capturas.

Sin Qt.
"""
from __future__ import annotations

import json
import urllib.error
from urllib import request

URL = "https://api.deepseek.com/v1/chat/completions"
ESPERA = 60  # segundos


class ErrorDeIA(Exception):
    """Algo salió mal al pedir la guía. El mensaje ya viene listo para
    enseñarse tal cual."""


def preguntar(llave: str, cuerpo: dict, url: str = URL) -> str:
    """El texto que contestó el modelo.

    Revienta con `ErrorDeIA` y un mensaje en palabras de Bruno. Quien llama
    lo enseña y **no bloquea nada**: exportar sigue funcionando sin guía.
    """
    if not str(llave or "").strip():
        raise ErrorDeIA("Falta la llave. Pégala aquí arriba y vuelve a intentar.")

    peticion = request.Request(
        url,
        data=json.dumps(cuerpo).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + str(llave).strip(),
        },
        method="POST",
    )

    try:
        with request.urlopen(peticion, timeout=ESPERA) as respuesta:
            crudo = respuesta.read()
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise ErrorDeIA("La llave no sirve. Revísala y vuelve a intentar.") from None
        if e.code == 429:
            raise ErrorDeIA("El servicio está saturado. Intenta en un minuto.") from None
        raise ErrorDeIA("No se pudo armar la guía: el servicio contestó con un error.") from None
    except urllib.error.URLError:
        raise ErrorDeIA("No se pudo armar la guía: no hay internet.") from None
    except OSError:
        raise ErrorDeIA("No se pudo armar la guía: falló la conexión.") from None

    try:
        datos = json.loads(crudo)
        return str(datos["choices"][0]["message"]["content"])
    except (json.JSONDecodeError, ValueError, KeyError, IndexError, TypeError):
        raise ErrorDeIA("El servicio contestó algo que no se entiende.") from None
