"""cotizador.py — lo que llega del Cotizador

El Cotizador (tu artefacto de claude.ai) es donde haces las cotizaciones. El panel
no lo sustituye: recibe una copia de sus datos en un archivo y los analiza.

El archivo trae cotizaciones, clientes de mensualidad, movimientos y tus tarifas
(entre ellas los factores con los que el Cotizador calcula tus costos). Aquí se
revisa, se le quita lo que el panel no necesita y se guarda en la base.

Importar reemplaza: lo que había de una importación anterior se cambia por lo nuevo.
"""

import json
import time

# Las claves de servicio del Cotizador y el nombre con que aparecen en la página.
SERVICIOS = {
    "n8n": "Automatización con n8n",
    "prog": "Programación",
    "wifi": "WiFi y access points",
    "cctv": "Cámaras de seguridad",
    "sw": "Instalación de programas",
    "mant": "Mantenimiento",
    "p3d": "Impresión 3D",
    "anl": "Análisis de mejora",
    "rep": "Reparación",
    "libre": "Otro",
}

LISTAS = ("cotizaciones", "clientes", "movimientos")
MAXIMO = 5000   # renglones por lista; de sobra para años de trabajo
# Datos de contacto de personas: el análisis no los usa, así que no se guardan.
SOBRAN = {"contacto", "telefono", "correo", "email", "direccion", "rfc"}


class ArchivoInvalido(ValueError):
    pass


def _limpio(documento):
    return {clave: valor for clave, valor in documento.items() if clave not in SOBRAN}


def importar(bd, archivo):
    """Guarda el contenido del archivo y regresa cuántos renglones entraron de cada cosa."""
    if not isinstance(archivo, dict) or not any(isinstance(archivo.get(lista), list) for lista in LISTAS):
        raise ArchivoInvalido("Ese archivo no parece venir del Cotizador.")

    cuenta = {}
    bd.execute("DELETE FROM cotizador")
    for lista in LISTAS:
        renglones = archivo.get(lista) or []
        if not isinstance(renglones, list) or len(renglones) > MAXIMO:
            raise ArchivoInvalido(f"La lista «{lista}» no se puede leer.")
        validos = [r for r in renglones if isinstance(r, dict) and r.get("id")]
        for renglon in validos:
            bd.execute("INSERT OR REPLACE INTO cotizador (tipo, id, datos) VALUES (?, ?, ?)",
                       (lista, str(renglon["id"])[:80], json.dumps(_limpio(renglon), ensure_ascii=False)))
        cuenta[lista] = len(validos)

    tarifas = (archivo.get("config") or {}).get("tarifas")
    if isinstance(tarifas, dict):
        # Solo números y textos cortos: son ajustes, no hay por qué guardar otra cosa.
        tarifas = {str(k)[:40]: v for k, v in tarifas.items() if isinstance(v, (int, float, str)) and len(str(v)) < 40}
        bd.execute("INSERT OR REPLACE INTO cotizador (tipo, id, datos) VALUES ('config', 'tarifas', ?)",
                   (json.dumps(tarifas),))

    resumen = {"fecha": time.strftime("%Y-%m-%d %H:%M"), **cuenta}
    bd.execute("INSERT OR REPLACE INTO cotizador (tipo, id, datos) VALUES ('config', 'importacion', ?)",
               (json.dumps(resumen),))
    return resumen


def leer(bd):
    """Todo lo importado, listo para analisis.py."""
    datos = {lista: [] for lista in LISTAS}
    datos.update(tarifas={}, importacion=None)
    for fila in bd.execute("SELECT tipo, id, datos FROM cotizador"):
        contenido = json.loads(fila["datos"])
        if fila["tipo"] == "config":
            datos[fila["id"]] = contenido
        elif fila["tipo"] in datos:
            datos[fila["tipo"]].append(contenido)
    return datos
