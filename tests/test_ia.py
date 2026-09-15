import json
import urllib.error

import pytest

from clasificador_video import ia


class _RespuestaFalsa:
    def __init__(self, payload: dict):
        self._datos = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._datos

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_devuelve_el_texto_del_modelo(monkeypatch):
    monkeypatch.setattr(
        ia.request, "urlopen",
        lambda req, timeout=None: _RespuestaFalsa(
            {"choices": [{"message": {"content": '{"orden": []}'}}]}
        ),
    )
    assert ia.preguntar("sk-123456789abcd", {"model": "x", "messages": []}) == '{"orden": []}'


def test_sin_llave_lo_dice_en_palabras(monkeypatch):
    with pytest.raises(ia.ErrorDeIA) as e:
        ia.preguntar("", {"model": "x", "messages": []})
    assert "llave" in str(e.value).lower()


def test_sin_internet_lo_dice_en_palabras(monkeypatch):
    def cae(req, timeout=None):
        raise urllib.error.URLError("nodename nor servname provided")

    monkeypatch.setattr(ia.request, "urlopen", cae)
    with pytest.raises(ia.ErrorDeIA) as e:
        ia.preguntar("sk-123456789abcd", {"model": "x", "messages": []})
    # En palabras de Bruno, no «URLError».
    assert "URLError" not in str(e.value)
    assert "internet" in str(e.value).lower()


def test_una_llave_que_no_sirve_lo_dice_en_palabras(monkeypatch):
    def rechaza(req, timeout=None):
        raise urllib.error.HTTPError("url", 401, "Unauthorized", {}, None)

    monkeypatch.setattr(ia.request, "urlopen", rechaza)
    with pytest.raises(ia.ErrorDeIA) as e:
        ia.preguntar("sk-mala", {"model": "x", "messages": []})
    assert "401" not in str(e.value)
    assert "llave" in str(e.value).lower()


def test_el_error_nunca_lleva_la_llave_adentro(monkeypatch):
    # El texto del error termina en pantalla y puede acabar en una captura.
    def cae(req, timeout=None):
        raise urllib.error.URLError("boom")

    monkeypatch.setattr(ia.request, "urlopen", cae)
    with pytest.raises(ia.ErrorDeIA) as e:
        ia.preguntar("sk-secretisima-999", {"model": "x", "messages": []})
    assert "sk-secretisima-999" not in str(e.value)


def test_una_respuesta_con_otra_forma_no_revienta_fea(monkeypatch):
    monkeypatch.setattr(
        ia.request, "urlopen",
        lambda req, timeout=None: _RespuestaFalsa({"otra": "cosa"}),
    )
    with pytest.raises(ia.ErrorDeIA):
        ia.preguntar("sk-123456789abcd", {"model": "x", "messages": []})
