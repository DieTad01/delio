"""app.py — el servidor del panel

Es lo único del sitio que "corre": lo demás son archivos que Nginx entrega tal cual.
Nginx le pasa a este programa todo lo que empieza con /api/ y nada más.

Rutas públicas (cualquiera las puede llamar):
    POST /api/solicitudes    guarda una solicitud del formulario de la página
    GET  /api/estado         dice si hay sesión abierta
    POST /api/entrar         abre sesión con la contraseña

Rutas privadas (necesitan sesión):
    GET    /api/panel              todos los datos del panel
    POST   /api/<tabla>            agrega un ingreso, objetivo o nota
    PATCH  /api/<tabla>/<id>       cambia el estado de una solicitud u objetivo
    DELETE /api/<tabla>/<id>       borra un renglón
    POST   /api/cotizador          recibe el archivo con los datos del Cotizador
    GET    /api/respaldo           descarga todos los datos en un archivo
    POST   /api/acceso/cerrar-otras   cierra las sesiones abiertas en otros dispositivos
    POST   /api/salir              cierra la sesión

Para probarlo en tu PC:  python servidor/app.py   y abre http://localhost:8765/panel.html
"""

import os
import re
import sys
from functools import wraps
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))   # para que "import almacen" funcione se arranque desde donde se arranque

import acceso      # noqa: E402
import almacen     # noqa: E402
import analisis    # noqa: E402
import cotizador   # noqa: E402
import sitio       # noqa: E402
import visitas     # noqa: E402

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024   # tope general: 2 MB (el archivo del Cotizador)
TOPE_PUBLICO = 16 * 1024                             # el formulario público no necesita más de 16 KB
COOKIE_SEGURA = True                           # la cookie solo viaja por HTTPS (en tu PC se apaga abajo)

# Frenos por dirección IP (ver acceso.py)
freno_entrar = acceso.Freno(maximo=5, segundos=15 * 60)        # 5 contraseñas malas: 15 minutos de espera
freno_solicitud = acceso.Freno(maximo=5, segundos=10 * 60)     # 5 solicitudes cada 10 minutos por persona
freno_del_dia = acceso.Freno(maximo=150, segundos=24 * 60 * 60)  # y 150 al día entre todos

# Qué puede escribir el panel en cada tabla: columna -> largo máximo.
# Lo que no esté aquí se ignora aunque venga en la petición.
CREAR = {
    "ingresos": {"fecha": 10, "cliente": 80, "servicio": 60, "concepto": 200, "monto": None},
    "objetivos": {"titulo": 120, "meta": 400, "limite": 10},
    "notas": {"texto": 2000},
}
CAMBIAR = {
    "solicitudes": {"estado": {"nueva", "cotizada", "ganada", "perdida"}, "nota": 400},
    "objetivos": {"estado": {"activo", "logrado", "pausado"}},
}
BORRAR = {"solicitudes", "ingresos", "objetivos", "notas"}
FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ---------- Ayudas ----------

def quien():
    """La IP de quien llama. Nginx la manda en X-Real-IP; sin Nginx (en tu PC) es la conexión directa."""
    return request.headers.get("X-Real-IP") or request.remote_addr or "?"


def aparato():
    """Cómo se presenta el navegador (para reconocer tus dispositivos en la bitácora)."""
    return request.headers.get("User-Agent", "")[:200]


def recorte(valor, largo):
    return str(valor if valor is not None else "").strip()[:largo]


def cuerpo():
    datos = request.get_json(silent=True)
    return datos if isinstance(datos, dict) else {}


def falla(mensaje, codigo=400):
    return jsonify(error=mensaje), codigo


def privado(funcion):
    """Marca una ruta como solo para quien tiene sesión abierta."""
    @wraps(funcion)
    def protegida(*args, **kwargs):
        # El panel manda este encabezado en cada petición. Una página ajena no puede
        # ponerlo, así que no puede hacer que tu navegador mande órdenes sin que lo sepas.
        if request.method != "GET" and request.headers.get("X-Delio") != "panel":
            return falla("Petición no permitida.", 403)
        with almacen.abrir() as bd:
            dentro = acceso.sesion_valida(bd, request.cookies.get(acceso.COOKIE))
        if not dentro:
            return falla("Necesitas iniciar sesión.", 401)
        return funcion(*args, **kwargs)
    return protegida


@app.after_request
def sin_memoria(respuesta):
    # Lo que responde el panel son datos privados: que ningún navegador ni intermediario los guarde.
    respuesta.headers.setdefault("Cache-Control", "no-store")
    return respuesta


# ---------- Público: el formulario de la página ----------

@app.post("/api/solicitudes")
def recibir_solicitud():
    ip = quien()
    if (request.content_length or 0) > TOPE_PUBLICO:
        return falla("El mensaje es demasiado largo.", 413)
    if freno_solicitud.lleno(ip) or freno_del_dia.lleno("todos"):
        return falla("Demasiadas solicitudes. Intenta más tarde.", 429)

    datos = cuerpo()
    solicitud = {
        "creada": almacen.ahora(),
        "nombre": recorte(datos.get("nombre"), 80),
        "negocio": recorte(datos.get("negocio"), 80),
        "contacto": recorte(datos.get("contacto"), 80),
        "servicio": recorte(datos.get("servicio"), 60),
        "mensaje": recorte(datos.get("mensaje"), 1500),
    }
    if not solicitud["nombre"] or not solicitud["mensaje"]:
        return falla("Faltan el nombre o el mensaje.")

    with almacen.abrir() as bd:
        almacen.insertar(bd, "solicitudes", solicitud)
    freno_solicitud.anotar(ip)
    freno_del_dia.anotar("todos")
    return jsonify(ok=True), 201


# ---------- Sesión ----------

@app.get("/api/estado")
def estado():
    with almacen.abrir() as bd:
        dentro = acceso.sesion_valida(bd, request.cookies.get(acceso.COOKIE))
    return jsonify(dentro=dentro, clave_lista=acceso.clave_configurada())


@app.post("/api/entrar")
def entrar():
    ip, datos = quien(), cuerpo()
    if not acceso.clave_configurada():
        return falla("El panel todavía no tiene contraseña: escríbela en DELIO_CLAVE (mínimo 10 caracteres) y reinicia el servidor.", 503)
    if freno_entrar.lleno(ip):
        with almacen.abrir() as bd:
            acceso.anotar(bd, "bloqueado por demasiados intentos", ip, aparato())
        return falla("Demasiados intentos. Espera 15 minutos.", 429)

    if not acceso.clave_correcta(recorte(datos.get("clave"), 200), os.environ["DELIO_CLAVE"]):
        freno_entrar.anotar(ip)
        with almacen.abrir() as bd:
            acceso.anotar(bd, "intento fallido", ip, aparato())
        return falla("Contraseña incorrecta.", 401)

    freno_entrar.limpiar(ip)
    with almacen.abrir() as bd:
        codigo = acceso.abrir_sesion(bd, ip, aparato())
        acceso.anotar(bd, "entró", ip, aparato())
    respuesta = jsonify(ok=True)
    # httponly: el JavaScript no puede leerla.  samesite=Strict: no viaja en peticiones que nacen en otro sitio.
    respuesta.set_cookie(acceso.COOKIE, codigo, max_age=acceso.DURACION, httponly=True,
                         secure=COOKIE_SEGURA, samesite="Strict", path="/api")
    return respuesta


@app.post("/api/salir")
@privado
def salir():
    with almacen.abrir() as bd:
        acceso.cerrar_sesion(bd, request.cookies.get(acceso.COOKIE))
        acceso.anotar(bd, "salió", quien(), aparato())
    respuesta = jsonify(ok=True)
    respuesta.delete_cookie(acceso.COOKIE, path="/api")
    return respuesta


@app.post("/api/acceso/cerrar-otras")
@privado
def cerrar_otras():
    with almacen.abrir() as bd:
        cerradas = acceso.cerrar_las_demas(bd, request.cookies.get(acceso.COOKIE))
        acceso.anotar(bd, f"cerró {cerradas} sesión(es) de otros dispositivos", quien(), aparato())
    return jsonify(cerradas=cerradas)


# ---------- Privado: los datos ----------

@app.get("/api/panel")
@privado
def panel():
    with almacen.abrir() as bd:
        resumen_visitas = visitas.actualizar(bd)
        return jsonify(
            cuentas=analisis.resumen(bd, resumen_visitas),
            solicitudes=almacen.listar(bd, "solicitudes"),
            ingresos=almacen.listar(bd, "ingresos"),
            objetivos=almacen.listar(bd, "objetivos"),
            notas=almacen.listar(bd, "notas"),
            visitas=resumen_visitas,
            servicios=list(sitio.servicios().values()),
            acceso={
                "sesiones": acceso.sesiones_abiertas(bd, request.cookies.get(acceso.COOKIE)),
                "bitacora": acceso.bitacora(bd),
            },
            hoy=almacen.hoy(),
        )


@app.get("/api/respaldo")
@privado
def respaldo():
    """Todos los datos del negocio en un archivo, para guardar una copia fuera del servidor."""
    with almacen.abrir() as bd:
        copia = {tabla: almacen.listar(bd, tabla, 100_000)
                 for tabla in ("solicitudes", "ingresos", "objetivos", "notas")}
        copia["cotizador"] = cotizador.leer(bd)
        copia["visitas"] = [dict(fila) for fila in bd.execute("SELECT * FROM visitas ORDER BY fecha")]
        copia["interes"] = [dict(fila) for fila in bd.execute("SELECT * FROM interes ORDER BY fecha")]
        acceso.anotar(bd, "descargó un respaldo", quien(), aparato())
    respuesta = jsonify(creado=almacen.ahora(), **copia)
    respuesta.headers["Content-Disposition"] = f'attachment; filename="delio-respaldo-{almacen.hoy()}.json"'
    return respuesta


@app.post("/api/<tabla>")
@privado
def agregar(tabla):
    if tabla not in CREAR:
        return falla("No existe.", 404)
    datos, fila = cuerpo(), {}
    for columna, largo in CREAR[tabla].items():
        if columna == "monto":
            try:
                fila["monto"] = round(float(datos.get("monto")), 2)
            except (TypeError, ValueError):
                return falla("El monto debe ser un número.")
            if not 0 < fila["monto"] < 100_000_000:
                return falla("El monto debe ser mayor a cero.")
        else:
            fila[columna] = recorte(datos.get(columna), largo)

    if tabla == "ingresos":
        fila["fecha"] = fila["fecha"] or almacen.hoy()
    if "fecha" in fila and not FECHA.match(fila["fecha"]):
        return falla("La fecha debe ser AAAA-MM-DD.")
    if fila.get("limite") and not FECHA.match(fila["limite"]):
        return falla("La fecha límite debe ser AAAA-MM-DD.")
    if tabla == "objetivos":
        if not fila["titulo"]:
            return falla("Escribe el objetivo.")
        fila["creado"] = almacen.hoy()
    if tabla == "notas":
        if not fila["texto"]:
            return falla("La nota está vacía.")
        fila["creada"] = almacen.ahora()

    with almacen.abrir() as bd:
        identificador = almacen.insertar(bd, tabla, fila)
    return jsonify(id=identificador), 201


@app.patch("/api/<tabla>/<int:identificador>")
@privado
def modificar(tabla, identificador):
    if tabla not in CAMBIAR:
        return falla("No existe.", 404)
    datos, cambios = cuerpo(), {}
    for columna, regla in CAMBIAR[tabla].items():
        if columna not in datos:
            continue
        if isinstance(regla, set):          # la regla es una lista de valores permitidos
            if datos[columna] not in regla:
                return falla("Valor no permitido.")
            cambios[columna] = datos[columna]
        else:                               # la regla es un largo máximo
            cambios[columna] = recorte(datos[columna], regla)
    if not cambios:
        return falla("Nada que cambiar.")
    with almacen.abrir() as bd:
        encontrado = almacen.cambiar(bd, tabla, identificador, cambios)
    return (jsonify(ok=True), 200) if encontrado else falla("No existe.", 404)


@app.delete("/api/<tabla>/<int:identificador>")
@privado
def quitar(tabla, identificador):
    if tabla not in BORRAR:
        return falla("No existe.", 404)
    with almacen.abrir() as bd:
        encontrado = almacen.borrar(bd, tabla, identificador)
    return (jsonify(ok=True), 200) if encontrado else falla("No existe.", 404)


# ---------- Privado: los datos del Cotizador ----------

@app.post("/api/cotizador")
@privado
def importar_cotizador():
    """Recibe el archivo del Cotizador y reemplaza lo que hubiera de una importación anterior."""
    try:
        with almacen.abrir() as bd:
            resumen = cotizador.importar(bd, cuerpo())
            acceso.anotar(bd, "importó datos del Cotizador", quien(), aparato())
    except cotizador.ArchivoInvalido as error:
        return falla(str(error))
    return jsonify(resumen)


@app.errorhandler(404)
def no_existe(_):
    return falla("No existe.", 404)


@app.errorhandler(413)
def muy_grande(_):
    return falla("El archivo es demasiado grande.", 413)


almacen.preparar()


# ---------- Solo para probar en tu PC ----------
# En el VPS este bloque no corre: ahí lo arranca gunicorn (ver delio-panel.service)
# y los archivos del sitio los entrega Nginx.

def leer_ajustes(archivo):
    """Lee un archivo de ajustes con renglones CLAVE=valor (el mismo formato que usa el VPS)."""
    if not archivo.exists():
        return
    for renglon in archivo.read_text(encoding="utf-8").splitlines():
        if "=" in renglon and not renglon.lstrip().startswith("#"):
            clave, valor = renglon.split("=", 1)
            os.environ.setdefault(clave.strip(), valor.strip())


if __name__ == "__main__":
    leer_ajustes(AQUI / "local.env")
    COOKIE_SEGURA = False   # en tu PC no hay HTTPS
    SITIO = AQUI.parent
    PERMITIDOS = re.compile(r"^(index|panel|aviso-de-privacidad)\.html$|^(css|js|img)/[\w.-]+$")

    @app.after_request
    def como_en_el_vps(respuesta):
        # La misma regla que pone Nginx (nginx/delio.conf), para que en tu PC se comporte igual.
        respuesta.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; form-action 'self' https://wa.me; "
            "frame-ancestors 'none'; base-uri 'self'; object-src 'none'")
        return respuesta

    @app.route("/visto", methods=["GET", "POST"])
    def visto():
        return "", 204

    @app.get("/")
    @app.get("/<path:archivo>")
    def sitio(archivo="index.html"):
        if not PERMITIDOS.match(archivo):
            return falla("No existe.", 404)
        return send_from_directory(SITIO, archivo, max_age=0)

    almacen.preparar()
    print("Panel en http://localhost:8765/panel.html  (Ctrl + C para detenerlo)")
    app.run(host="127.0.0.1", port=8765, threaded=True)
