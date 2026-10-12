"""visitas.py — cuánta gente entra a la página

No usa cookies ni servicios de fuera. Nginx ya escribe una línea por cada
archivo que entrega; aquí se leen esas líneas y se cuenta:

  - vistas:      veces que se abrió la portada
  - visitantes:  direcciones IP distintas ese día (una aproximación de "personas")
  - interés:     qué servicio abrieron en "Qué incluye" (js/detalle.js avisa con /visto?s=clave)
  - origen:      desde qué sitio llegaron

Nginx solo conserva unos 14 días de registros, así que los totales de cada día
se copian a la base para no perder la historia. Las IP no se guardan en la base.
"""

import glob
import gzip
import os
import re
from collections import Counter
from urllib.parse import parse_qs, urlsplit

# Una línea del registro de Nginx (formato "combined"):
# 1.2.3.4 - - [11/Oct/2026:15:55:48 +0000] "GET / HTTP/1.1" 200 5329 "https://google.com/" "Mozilla/5.0 ..."
LINEA = re.compile(
    r'(?P<ip>\S+) \S+ \S+ \[(?P<dia>\d{2})/(?P<mes>\w{3})/(?P<anio>\d{4}):[^\]]+\] '
    r'"(?P<metodo>[A-Z]+) (?P<ruta>\S+)[^"]*" (?P<estado>\d{3}) \S+ "(?P<origen>[^"]*)" "(?P<agente>[^"]*)"'
)
MESES = {nombre: f"{numero:02d}" for numero, nombre in enumerate(
    "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), start=1)}

# Programas automáticos (buscadores, vistas previas de enlaces, escáneres): no son clientes.
ROBOT = re.compile(r"bot|crawl|spider|slurp|curl|wget|python|scan|monitor|headless|preview|"
                   r"facebookexternalhit|whatsapp|lighthouse|http", re.IGNORECASE)
CLAVE = re.compile(r"^[a-z0-9]{1,20}$")
PORTADA = {"/", "/index.html"}


def _es_robot(agente):
    # Los navegadores de verdad siempre se presentan como "Mozilla/…".
    return not agente.startswith("Mozilla/") or bool(ROBOT.search(agente.split(" ", 1)[-1]))


def leer(patron=None, dominio="delioph.tech"):
    """Lee los registros y regresa (días, orígenes, problema).

    días:     {"2026-10-11": {"vistas": 3, "ips": {...}, "interes": Counter()}}
    orígenes: Counter({"google.com": 4, ...})
    problema: texto si no se pudo leer nada; si no, None
    """
    patron = patron or os.environ.get("DELIO_LOG") or "/var/log/nginx/delio.access.log*"
    archivos = glob.glob(patron)
    if not archivos:
        return {}, Counter(), f"No hay registros en {patron}"

    dias, origenes, problema = {}, Counter(), None
    for archivo in archivos:
        # Los registros viejos vienen comprimidos (.gz).
        abridor = gzip.open if archivo.endswith(".gz") else open
        try:
            with abridor(archivo, "rt", encoding="utf-8", errors="replace") as lineas:
                for linea in lineas:
                    _contar(linea, dias, origenes, dominio)
        except OSError as error:
            problema = f"No se pudo leer {archivo}: {error.strerror}"
    return dias, origenes, (problema if not dias else None)


def _contar(linea, dias, origenes, dominio):
    dato = LINEA.match(linea)
    if not dato or dato["mes"] not in MESES or _es_robot(dato["agente"]):
        return
    fecha = f'{dato["anio"]}-{MESES[dato["mes"]]}-{dato["dia"]}'
    dia = dias.setdefault(fecha, {"vistas": 0, "ips": set(), "interes": Counter()})
    partes = urlsplit(dato["ruta"])

    if dato["metodo"] == "GET" and partes.path in PORTADA and dato["estado"] in ("200", "304"):
        dia["vistas"] += 1
        dia["ips"].add(dato["ip"])
        sitio = urlsplit(dato["origen"]).hostname or ""
        if sitio and not sitio.endswith(dominio):
            origenes[sitio.removeprefix("www.")] += 1

    elif partes.path == "/visto":
        clave = parse_qs(partes.query).get("s", [""])[0]
        if CLAVE.match(clave):
            dia["interes"][clave] += 1


def actualizar(bd):
    """Lee los registros, guarda los totales por día y regresa el resumen para el panel."""
    dias, origenes, problema = leer()

    for fecha, dia in dias.items():
        # MAX: si el registro de un día viejo ya se borró a medias, se queda la cuenta más alta.
        bd.execute(
            "INSERT INTO visitas (fecha, vistas, visitantes) VALUES (?, ?, ?) "
            "ON CONFLICT(fecha) DO UPDATE SET vistas = MAX(vistas, excluded.vistas), "
            "visitantes = MAX(visitantes, excluded.visitantes)",
            (fecha, dia["vistas"], len(dia["ips"])),
        )
        for servicio, veces in dia["interes"].items():
            bd.execute(
                "INSERT INTO interes (fecha, servicio, veces) VALUES (?, ?, ?) "
                "ON CONFLICT(fecha, servicio) DO UPDATE SET veces = MAX(veces, excluded.veces)",
                (fecha, servicio, veces),
            )

    por_dia = [dict(fila) for fila in bd.execute(
        "SELECT fecha, vistas, visitantes FROM visitas ORDER BY fecha DESC LIMIT 30")]
    interes = [dict(fila) for fila in bd.execute(
        "SELECT servicio, SUM(veces) AS veces FROM interes "
        "WHERE fecha >= date('now', 'localtime', '-30 days') GROUP BY servicio ORDER BY veces DESC")]
    return {
        "por_dia": por_dia,
        "interes": interes,
        "origenes": [{"sitio": sitio, "veces": veces} for sitio, veces in origenes.most_common(8)],
        "problema": problema,
    }
