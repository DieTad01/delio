"""acceso.py — el control de acceso al panel

Cuatro piezas:
  1. La contraseña. Se escribe tal cual en el archivo de ajustes (DELIO_CLAVE),
     que no se sube a GitHub y en el VPS solo puede leer el administrador.
  2. La sesión. Al entrar, el navegador recibe una cookie con un código al azar;
     la base guarda solo la huella de ese código, cuándo vence y desde dónde se abrió.
  3. Los frenos. Cuentan intentos por dirección IP para que nadie pueda probar
     contraseñas sin parar ni llenar la base desde el formulario público.
  4. La bitácora. Cada entrada, salida e intento fallido queda anotado, para que
     puedas ver si alguien más anduvo tocando la puerta.
"""

import hashlib
import hmac
import os
import secrets
import threading
import time

VUELTAS = 600_000                  # qué tan lento (y difícil de adivinar a la fuerza) es el hash
DURACION = 7 * 24 * 60 * 60        # una sesión dura como máximo 7 días…
INACTIVIDAD = 12 * 60 * 60         # …y se cierra sola tras 12 horas sin usarse
BITACORA = 300                     # cuántos renglones conserva la bitácora
COOKIE = "delio_sesion"


# ---------- 1. Contraseña ----------

def crear_hash(clave):
    sal = secrets.token_bytes(16)   # un dato al azar: dos contraseñas iguales dan hashes distintos
    huella = hashlib.pbkdf2_hmac("sha256", clave.encode("utf-8"), sal, VUELTAS)
    return f"pbkdf2:{VUELTAS}:{sal.hex()}:{huella.hex()}"


MINIMO = 10   # una contraseña más corta no se acepta


def clave_correcta(clave, guardado):
    # Lo normal: la contraseña está escrita tal cual en los ajustes.
    if not guardado.startswith("pbkdf2:"):
        # compare_digest tarda lo mismo acierte o no, para no dar pistas con el tiempo de respuesta.
        return hmac.compare_digest(clave.encode("utf-8"), guardado.encode("utf-8"))
    # También se acepta un hash hecho con crear_hash(), por si un día prefieres no guardarla legible.
    try:
        _, vueltas, sal, esperado = guardado.split(":")
        huella = hashlib.pbkdf2_hmac("sha256", clave.encode("utf-8"), bytes.fromhex(sal), int(vueltas))
    except (ValueError, AttributeError):
        return False
    return hmac.compare_digest(huella.hex(), esperado)


def clave_configurada():
    return len(os.environ.get("DELIO_CLAVE", "")) >= MINIMO


# ---------- 2. Sesión ----------

def _huella(codigo):
    return hashlib.sha256(codigo.encode("utf-8")).hexdigest()


def _sello():
    """Una marca de la contraseña vigente. Si la cambias, la marca cambia y todas
    las sesiones abiertas dejan de valer."""
    return hashlib.sha256(os.environ.get("DELIO_CLAVE", "").encode("utf-8")).hexdigest()[:16]


def abrir_sesion(bd, ip="", agente=""):
    codigo = secrets.token_urlsafe(32)
    ahora = int(time.time())
    bd.execute("DELETE FROM sesiones WHERE vence < ? OR usada < ? OR sello != ?",
               (ahora, ahora - INACTIVIDAD, _sello()))
    bd.execute("INSERT INTO sesiones (huella, sello, creada, usada, vence, ip, agente) VALUES (?, ?, ?, ?, ?, ?, ?)",
               (_huella(codigo), _sello(), ahora, ahora, ahora + DURACION, ip, agente[:200]))
    return codigo


def sesion_valida(bd, codigo):
    if not codigo:
        return False
    ahora = int(time.time())
    fila = bd.execute("SELECT sello, usada, vence FROM sesiones WHERE huella = ?", (_huella(codigo),)).fetchone()
    if not fila or fila["sello"] != _sello() or fila["vence"] < ahora or fila["usada"] < ahora - INACTIVIDAD:
        return False
    if ahora - fila["usada"] > 60:   # no hace falta escribir en la base en cada clic
        bd.execute("UPDATE sesiones SET usada = ? WHERE huella = ?", (ahora, _huella(codigo)))
    return True


def cerrar_sesion(bd, codigo):
    if codigo:
        bd.execute("DELETE FROM sesiones WHERE huella = ?", (_huella(codigo),))


def cerrar_las_demas(bd, codigo):
    return bd.execute("DELETE FROM sesiones WHERE huella != ?", (_huella(codigo or ""),)).rowcount


def sesiones_abiertas(bd, codigo):
    ahora = int(time.time())
    filas = bd.execute(
        "SELECT huella, creada, usada, ip, agente FROM sesiones "
        "WHERE vence > ? AND usada > ? AND sello = ? ORDER BY usada DESC",
        (ahora, ahora - INACTIVIDAD, _sello()))
    actual = _huella(codigo or "")
    return [{"creada": fila["creada"], "usada": fila["usada"], "ip": fila["ip"], "agente": fila["agente"],
             "esta": fila["huella"] == actual} for fila in filas]


# ---------- 3. Frenos ----------

class Freno:
    """Deja pasar como máximo `maximo` veces cada `segundos`, por cada clave (una IP)."""

    def __init__(self, maximo, segundos):
        self.maximo = maximo
        self.segundos = segundos
        self.veces = {}
        self.candado = threading.Lock()   # el servidor atiende varias peticiones a la vez

    def _recientes(self, clave):
        limite = time.time() - self.segundos
        recientes = [momento for momento in self.veces.get(clave, []) if momento > limite]
        self.veces[clave] = recientes
        return recientes

    def lleno(self, clave):
        with self.candado:
            return len(self._recientes(clave)) >= self.maximo

    def anotar(self, clave):
        with self.candado:
            self._recientes(clave).append(time.time())

    def limpiar(self, clave):
        with self.candado:
            self.veces.pop(clave, None)


# ---------- 4. Bitácora ----------

def anotar(bd, suceso, ip="", agente=""):
    bd.execute("INSERT INTO accesos (fecha, suceso, ip, agente) VALUES (?, ?, ?, ?)",
               (time.strftime("%Y-%m-%d %H:%M"), suceso, ip, agente[:200]))
    # Solo se conservan los más recientes: la bitácora no crece sin fin.
    bd.execute("DELETE FROM accesos WHERE id <= (SELECT MAX(id) FROM accesos) - ?", (BITACORA,))


def bitacora(bd, cuantos=40):
    return [dict(fila) for fila in bd.execute(
        "SELECT fecha, suceso, ip, agente FROM accesos ORDER BY id DESC LIMIT ?", (cuantos,))]
