# db.py
# Aquí está todo lo que Central necesita hacer con la base de datos SQLite.
# El resto del código nunca escribe SQL: siempre llama a las funciones de este fichero.

import os
import sqlite3
from datetime import datetime

# Ruta por defecto del fichero de la base de datos (junto a este mismo fichero).
# Si en Railway queremos guardarla en un volumen, se la pasamos a init_db().
RUTA_BD = os.path.join(os.path.dirname(__file__), "wm.db")


def obtener_conexion():
    """Abre una conexión nueva a la BD.
    Abrimos una por cada operación porque Central usa varios hilos y
    una conexión de SQLite no se debe compartir entre hilos."""
    conexion = sqlite3.connect(RUTA_BD)

    # Con esto las filas se pueden leer por nombre: fila["status"]
    conexion.row_factory = sqlite3.Row
    return conexion


def inicializar_bd(ruta=None):
    """Crea las tablas si todavía no existen.
    Se llama una sola vez al arrancar Central."""
    global RUTA_BD

    if ruta is not None:
        RUTA_BD = ruta

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    # Operarios: solo necesitamos su identificador y un nombre
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS operators (
            id   TEXT PRIMARY KEY,
            name TEXT
        )
    """)

    # Estaciones de riego: id, ubicación, estado actual y última vez que se supo de ella
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stations (
            id        TEXT PRIMARY KEY,
            location  TEXT,
            status    TEXT,
            last_seen TEXT
        )
    """)

    conexion.commit()
    conexion.close()


# ---------------------------------------------------------------
# OPERARIOS
# ---------------------------------------------------------------

def agregar_operario(identificador, nombre):
    """Da de alta un operario. Si ya existía, le actualiza el nombre."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    if existe_operario(identificador):
        cursor.execute(
            "UPDATE operators SET name = ? WHERE id = ?",
            (nombre, identificador)
        )
    else:
        cursor.execute(
            "INSERT INTO operators (id, name) VALUES (?, ?)",
            (identificador, nombre)
        )

    conexion.commit()
    conexion.close()


def existe_operario(identificador):
    """Devuelve True si el operario está dado de alta.
    Central lo usa para validar las peticiones que llegan del FO."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cursor.execute(
        "SELECT id FROM operators WHERE id = ?",
        (identificador,)
    )

    fila = cursor.fetchone()
    conexion.close()

    return fila is not None


# ---------------------------------------------------------------
# ESTACIONES
# ---------------------------------------------------------------

def registrar_estacion(identificador, ubicacion):
    """Registra una estación nueva con su ubicación.
    Si ya estaba registrada, solo actualiza la ubicación y deja su estado como está."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    if existe_estacion(identificador):
        cursor.execute(
            "UPDATE stations SET location = ? WHERE id = ?",
            (ubicacion, identificador)
        )
    else:
        # Una estación nueva empieza como DESCONECTADA hasta que conecte de verdad
        cursor.execute(
            "INSERT INTO stations (id, location, status, last_seen) VALUES (?, ?, ?, ?)",
            (identificador, ubicacion, "DISCONNECTED", ahora())
        )

    conexion.commit()
    conexion.close()


def existe_estacion(identificador):
    """Devuelve True si la estación está registrada en la BD."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cursor.execute(
        "SELECT id FROM stations WHERE id = ?",
        (identificador,)
    )

    fila = cursor.fetchone()
    conexion.close()

    return fila is not None


def obtener_estacion(identificador):
    """Devuelve los datos de una estación como diccionario, o None si no existe."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cursor.execute(
        "SELECT * FROM stations WHERE id = ?",
        (identificador,)
    )

    fila = cursor.fetchone()
    conexion.close()

    if fila is None:
        return None

    return dict(fila)


def establecer_estado(identificador, estado):
    """Cambia el estado de una estación y apunta cuándo ocurrió.
    Los estados que usaremos son: ACTIVE, WATERING, LEAK,
    OUT_OF_SERVICE y DISCONNECTED."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cursor.execute(
        "UPDATE stations SET status = ?, last_seen = ? WHERE id = ?",
        (estado, ahora(), identificador)
    )

    conexion.commit()
    conexion.close()


def desconectar_todas_estaciones():
    """Pone todas las estaciones como DESCONECTADA.
    Se llama al arrancar Central: hasta que una estación conecte,
    Central no sabe cuál es su estado real."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cursor.execute(
        "UPDATE stations SET status = ?",
        ("DISCONNECTED",)
    )

    conexion.commit()
    conexion.close()


def listar_estaciones():
    """Devuelve la lista de todas las estaciones (cada una como diccionario).
    Sirve para llenar el panel al arrancar."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cursor.execute("SELECT * FROM stations ORDER BY id")
    filas = cursor.fetchall()
    conexion.close()

    return [dict(fila) for fila in filas]


# ---------------------------------------------------------------
# AUXILIARES
# ---------------------------------------------------------------

def ahora():
    """Fecha y hora actual como texto, para guardarla en last_seen."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
