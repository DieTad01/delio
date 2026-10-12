"""sitio.py — lo que el panel lee de la página pública

La lista de servicios vive en un solo lugar: index.html. En vez de copiarla aquí
(y que un día no coincidan), este archivo la lee de ahí:

  - servicios():       {"wifi": "WiFi y access points", ...}  clave -> nombre
  - texto_publico():   el texto de la página, sin etiquetas
"""

from html.parser import HTMLParser
from pathlib import Path

INDEX = Path(__file__).resolve().parent.parent / "index.html"
_memoria = {"cambio": None, "servicios": {}, "texto": ""}


class _Lector(HTMLParser):
    """Recorre index.html una vez y junta las dos cosas."""

    SALTAR = {"form", "script", "style", "select"}

    def __init__(self):
        super().__init__()
        self.en_main = 0
        self.saltando = 0
        self.trozos = []
        self.servicios = {}
        self.clave = None           # el mosaico de servicio que se está leyendo
        self.en_nombre = False

    def handle_starttag(self, etiqueta, atributos):
        atributos = dict(atributos)
        if etiqueta == "main":
            self.en_main += 1
        if etiqueta in self.SALTAR:
            self.saltando += 1
        # <a class="servicio" data-detalle="wifi"> … <span class="servicio__nombre">WiFi…</span>
        if etiqueta == "a" and atributos.get("data-detalle"):
            self.clave = atributos["data-detalle"]
        if self.clave and "servicio__nombre" in (atributos.get("class") or ""):
            self.en_nombre = True

    def handle_endtag(self, etiqueta):
        if etiqueta == "main":
            self.en_main -= 1
        if etiqueta in self.SALTAR:
            self.saltando -= 1
        if etiqueta == "a":
            self.clave = None
        self.en_nombre = False

    def handle_data(self, texto):
        limpio = " ".join(texto.split())
        if not limpio:
            return
        if self.en_nombre and self.clave:
            self.servicios.setdefault(self.clave, limpio)
        if self.en_main and not self.saltando:
            self.trozos.append(limpio)


def _leer():
    """Vuelve a leer index.html solo si cambió desde la última vez."""
    try:
        cambio = INDEX.stat().st_mtime
        if cambio != _memoria["cambio"]:
            lector = _Lector()
            lector.feed(INDEX.read_text(encoding="utf-8"))
            _memoria.update(cambio=cambio, servicios=lector.servicios, texto="\n".join(lector.trozos))
    except OSError:
        _memoria.update(cambio=None, servicios={}, texto="(no se pudo leer index.html)")
    return _memoria


def servicios():
    return dict(_leer()["servicios"])


def texto_publico():
    return _leer()["texto"]
