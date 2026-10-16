import os
import sqlite3
from datetime import datetime

# Ruta por defecto del fichero de la base de datos (junto a este mismo fichero).
# Si en Railway queremos guardarla en un volumen, se la pasamos a ini_bd().
RUTA_BD = os.path.join(os.path.dirname(__file__), "wm.db")


def obt_conex():  # Abre una conexión nueva (una por operación: SQLite no se comparte entre hilos)
    conexion = sqlite3.connect(RUTA_BD)

    # Con esto las filas se pueden leer por nombre: fila["status"]
    conexion.row_factory = sqlite3.Row
    return conexion


def ini_bd(ruta=None):  # Crea las tablas si no existen. Se llama una vez al arrancar Central
    global RUTA_BD
    if ruta is not None:
        RUTA_BD = ruta
    conexion = obt_conex()
    cursor = conexion.cursor()

    cursor.execute("""CREATE TABLE IF NOT EXISTS operators (id   TEXT PRIMARY KEY,name TEXT) """)
    cursor.execute("""CREATE TABLE IF NOT EXISTS stations (id        TEXT PRIMARY KEY,location  TEXT,status    TEXT,last_seen TEXT)""")

    conexion.commit()
    conexion.close()


# ---------------------------------------------------------------
# OPERARIOS
# ---------------------------------------------------------------

def alta_oper(identificador, nombre):
    conexion = obt_conex()
    cursor = conexion.cursor()

    if hay_oper(identificador):
        cursor.execute("UPDATE operators SET name = ? WHERE id = ?",(nombre, identificador))
    else:
        cursor.execute("INSERT INTO operators (id, name) VALUES (?, ?)",(identificador, nombre))

    conexion.commit()
    conexion.close()


def hay_oper(identificador):
    conexion = obt_conex()
    cursor = conexion.cursor()

    cursor.execute("SELECT id FROM operators WHERE id = ?",(identificador,))

    fila = cursor.fetchone()
    conexion.close()

    return fila is not None


# ---------------------------------------------------------------
# ESTACIONES
# ---------------------------------------------------------------

def reg_estac(identificador, ubicacion):  # Registra una estación nueva (si ya existía, solo actualiza la ubicación)
    conexion = obt_conex()
    cursor = conexion.cursor()

    if hay_estac(identificador):
        cursor.execute("UPDATE stations SET location = ? WHERE id = ?",(ubicacion, identificador))
    else:
        # Una estación nueva empieza como DESCONECTADA hasta que conecte de verdad
        cursor.execute("INSERT INTO stations (id, location, status, last_seen) VALUES (?, ?, ?, ?)",(identificador, ubicacion, "DISCONNECTED", ahora()) )

    conexion.commit()
    conexion.close()


def hay_estac(identificador):
    conexion = obt_conex()
    cursor = conexion.cursor()

    cursor.execute("SELECT id FROM stations WHERE id = ?",(identificador,))

    fila = cursor.fetchone()
    conexion.close()

    return fila is not None


def obt_estac(identificador):  # Devuelve los datos de una estación como diccionario
    conexion = obt_conex()
    cursor = conexion.cursor()

    cursor.execute("SELECT * FROM stations WHERE id = ?",(identificador,) )

    fila = cursor.fetchone()
    conexion.close()

    if fila is None:
        return None

    return dict(fila)


def fij_estado(identificador, estado):  #Cambia el estado
    conexion = obt_conex()
    cursor = conexion.cursor()

    cursor.execute("UPDATE stations SET status = ?, last_seen = ? WHERE id = ?",(estado, ahora(), identificador))

    conexion.commit()
    conexion.close()


def desc_todas():
    conexion = obt_conex()
    cursor = conexion.cursor()

    cursor.execute("UPDATE stations SET status = ?",("DISCONNECTED",))

    conexion.commit()
    conexion.close()


def list_estac():
    conexion = obt_conex()
    cursor = conexion.cursor()

    cursor.execute("SELECT * FROM stations ORDER BY id")
    filas = cursor.fetchall()
    conexion.close()

    return [dict(fila) for fila in filas]


# ---------------------------------------------------------------
# AUXILIARES
# ---------------------------------------------------------------

def ahora(): 
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")