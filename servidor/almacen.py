"""almacen.py — la base de datos

Todo se guarda en un solo archivo de SQLite (delio.db). SQLite viene con Python:
no hay que instalar ni administrar un servidor de base de datos.

La carpeta del archivo sale de la variable DELIO_DATOS. En el VPS es
/var/lib/delio, fuera de la carpeta que Nginx entrega, para que nadie pueda
descargar la base escribiendo su dirección.
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent

ESQUEMA = """
CREATE TABLE IF NOT EXISTS solicitudes (
    id       INTEGER PRIMARY KEY,
    creada   TEXT NOT NULL,
    nombre   TEXT NOT NULL,
    negocio  TEXT NOT NULL DEFAULT '',
    contacto TEXT NOT NULL DEFAULT '',
    servicio TEXT NOT NULL DEFAULT '',
    mensaje  TEXT NOT NULL,
    estado   TEXT NOT NULL DEFAULT 'nueva',
    nota     TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS ingresos (
    id       INTEGER PRIMARY KEY,
    fecha    TEXT NOT NULL,
    cliente  TEXT NOT NULL DEFAULT '',
    servicio TEXT NOT NULL DEFAULT '',
    concepto TEXT NOT NULL DEFAULT '',
    monto    REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS objetivos (
    id     INTEGER PRIMARY KEY,
    creado TEXT NOT NULL,
    titulo TEXT NOT NULL,
    meta   TEXT NOT NULL DEFAULT '',
    limite TEXT NOT NULL DEFAULT '',
    estado TEXT NOT NULL DEFAULT 'activo'
);
CREATE TABLE IF NOT EXISTS notas (
    id     INTEGER PRIMARY KEY,
    creada TEXT NOT NULL,
    texto  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS cotizador (
    tipo  TEXT NOT NULL,
    id    TEXT NOT NULL,
    datos TEXT NOT NULL,
    PRIMARY KEY (tipo, id)
);
CREATE TABLE IF NOT EXISTS visitas (
    fecha      TEXT PRIMARY KEY,
    vistas     INTEGER NOT NULL,
    visitantes INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS interes (
    fecha    TEXT NOT NULL,
    servicio TEXT NOT NULL,
    veces    INTEGER NOT NULL,
    PRIMARY KEY (fecha, servicio)
);
CREATE TABLE IF NOT EXISTS sesiones (
    huella TEXT PRIMARY KEY,
    sello  TEXT NOT NULL,
    creada INTEGER NOT NULL,
    usada  INTEGER NOT NULL,
    vence  INTEGER NOT NULL,
    ip     TEXT NOT NULL DEFAULT '',
    agente TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS accesos (
    id     INTEGER PRIMARY KEY,
    fecha  TEXT NOT NULL,
    suceso TEXT NOT NULL,
    ip     TEXT NOT NULL DEFAULT '',
    agente TEXT NOT NULL DEFAULT ''
);
"""

# En qué orden se listan las tablas que muestra el panel.
ORDEN = {
    "solicitudes": "id DESC",
    "ingresos": "fecha DESC, id DESC",
    "objetivos": "id DESC",
    "notas": "id DESC",
}


def ruta():
    carpeta = Path(os.environ.get("DELIO_DATOS") or AQUI / "datos")
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta / "delio.db"


@contextmanager
def abrir():
    """Abre la base, guarda los cambios al terminar y la cierra.

    Se usa así:  with almacen.abrir() as bd: ...
    Si algo falla a la mitad, no se guarda nada de ese bloque.
    """
    bd = sqlite3.connect(ruta(), timeout=10)
    bd.row_factory = sqlite3.Row   # las filas se pueden leer por nombre de columna
    try:
        yield bd
        bd.commit()
    except BaseException:
        bd.rollback()
        raise
    finally:
        bd.close()


def preparar():
    """Crea las tablas si no existen. Se llama una vez, al arrancar."""
    with abrir() as bd:
        # WAL deja leer mientras alguien más escribe (varias pestañas, el formulario público).
        bd.execute("PRAGMA journal_mode=WAL")
        # La tabla de sesiones cambió de forma (ahora anota dispositivo y último uso).
        # Si existe la versión vieja se tira: lo único que se pierde es que hay que volver a entrar.
        columnas = {fila["name"] for fila in bd.execute("PRAGMA table_info(sesiones)")}
        if columnas and "sello" not in columnas:
            bd.execute("DROP TABLE sesiones")
        bd.execute("DROP TABLE IF EXISTS mensajes")   # la conversación con la IA, que ya no existe
        bd.executescript(ESQUEMA)


def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def hoy():
    return datetime.now().strftime("%Y-%m-%d")


# Los nombres de tabla y de columna nunca vienen de lo que escribe una persona:
# salen de las listas de app.py. Los valores siempre viajan aparte, con "?",
# y así nadie puede colar instrucciones de SQL dentro de un campo.

def listar(bd, tabla, limite=500):
    filas = bd.execute(f"SELECT * FROM {tabla} ORDER BY {ORDEN[tabla]} LIMIT ?", (limite,))
    return [dict(fila) for fila in filas]


def insertar(bd, tabla, datos):
    columnas = ", ".join(datos)
    huecos = ", ".join("?" for _ in datos)
    cursor = bd.execute(f"INSERT INTO {tabla} ({columnas}) VALUES ({huecos})", tuple(datos.values()))
    return cursor.lastrowid


def cambiar(bd, tabla, identificador, datos):
    cambios = ", ".join(f"{columna} = ?" for columna in datos)
    cursor = bd.execute(f"UPDATE {tabla} SET {cambios} WHERE id = ?", (*datos.values(), identificador))
    return cursor.rowcount > 0


def borrar(bd, tabla, identificador):
    return bd.execute(f"DELETE FROM {tabla} WHERE id = ?", (identificador,)).rowcount > 0
