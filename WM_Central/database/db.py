import os
import sqlite3
from datetime import datetime
import json
import threading

RUTA_BD = os.path.join(os.path.dirname(__file__), "wm.db")
RUTA_AUDIT_JSONL = os.path.join(os.path.dirname(__file__), "audit.jsonl")
_audit_lock = threading.Lock()

# Columnas añadidas en P2 (se migran de forma idempotente si la BD ya existía)
COLUMNAS_STATIONS = [
    ("total", "REAL DEFAULT 0"),
    ("registered", "INTEGER DEFAULT 0"),
    ("authenticated", "INTEGER DEFAULT 0"),
    ("symmetric_key", "TEXT"),
    ("key_status", "TEXT DEFAULT 'NONE'"),
    ("city", "TEXT"),
    ("temp_c", "REAL"),
    ("weather_condition", "TEXT"),
    ("weather_alert", "INTEGER DEFAULT 0"),
    ("weather_reason", "TEXT"),
    ("weather_updated_at", "TEXT"),
    ("pending_weather_stop", "INTEGER DEFAULT 0"),
]


def obt_conex():  # Abre una conexión nueva (una por operación: SQLite no se comparte entre hilos)
    conexion = sqlite3.connect(RUTA_BD)
    conexion.row_factory = sqlite3.Row
    return conexion


def ini_bd(ruta=None):  # Crea las tablas si no existen y migra columnas nuevas al arrancar Central
    global RUTA_BD, RUTA_AUDIT_JSONL
    if ruta is not None:
        RUTA_BD = ruta
        RUTA_AUDIT_JSONL = os.path.join(os.path.dirname(os.path.abspath(ruta)), "audit.jsonl")

    conexion = obt_conex()
    conexion.execute("CREATE TABLE IF NOT EXISTS operators (id TEXT PRIMARY KEY, name TEXT)")
    conexion.execute(
        "CREATE TABLE IF NOT EXISTS stations (id TEXT PRIMARY KEY, location TEXT, status TEXT, last_seen TEXT)"
    )

    for col, definicion in COLUMNAS_STATIONS:
        try:
            conexion.execute(f"ALTER TABLE stations ADD COLUMN {col} {definicion}")
        except sqlite3.OperationalError:
            pass  # La columna ya existe

    conexion.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            source    TEXT NOT NULL,
            actor     TEXT NOT NULL,
            ip        TEXT,
            action    TEXT NOT NULL,
            level     TEXT DEFAULT 'INFO',
            details   TEXT,
            params    TEXT
        )
        """
    )
    try:
        conexion.execute("ALTER TABLE audit_logs ADD COLUMN params TEXT")
    except sqlite3.OperationalError:
        pass  # La columna ya existe

    conexion.commit()
    conexion.close()


# Operarios
def alta_oper(identificador, nombre):
    conexion = obt_conex()

    if hay_oper(identificador):
        conexion.execute("UPDATE operators SET name = ? WHERE id = ?", (nombre, identificador))
    else:
        conexion.execute("INSERT INTO operators (id, name) VALUES (?, ?)", (identificador, nombre))

    conexion.commit()
    conexion.close()


def hay_oper(identificador):
    conexion = obt_conex()
    fila = conexion.execute("SELECT id FROM operators WHERE id = ?", (identificador,)).fetchone()
    conexion.close()

    return fila is not None


def list_opers():
    conexion = obt_conex()
    filas = conexion.execute("SELECT * FROM operators ORDER BY id").fetchall()
    conexion.close()

    return [dict(fila) for fila in filas]


# Estaciones
def reg_estac(identificador, ubicacion):  # Registra una estación nueva; si ya existía actualiza ubicación
    conexion = obt_conex()

    if hay_estac(identificador):
        conexion.execute(
            "UPDATE stations SET location = ?, city = COALESCE(city, ?) WHERE id = ?",
            (ubicacion, ubicacion, identificador),
        )
    else:
        # Una estación nueva empieza como DESCONECTADA hasta que se conecte de verdad
        conexion.execute(
            "INSERT INTO stations (id, location, city, status, last_seen) VALUES (?, ?, ?, ?, ?)",
            (identificador, ubicacion, ubicacion, "DISCONNECTED", ahora()),
        )

    conexion.commit()
    conexion.close()


def hay_estac(identificador):
    conexion = obt_conex()
    fila = conexion.execute("SELECT id FROM stations WHERE id = ?", (identificador,)).fetchone()
    conexion.close()

    return fila is not None


def obt_estac(identificador):  # Devuelve los datos de una estación como diccionario
    conexion = obt_conex()
    fila = conexion.execute("SELECT * FROM stations WHERE id = ?", (identificador,)).fetchone()
    conexion.close()

    if fila is None:
        return None

    return dict(fila)


def fij_estado(identificador, estado):  # Cambia el estado
    conexion = obt_conex()
    conexion.execute("UPDATE stations SET status = ?, last_seen = ? WHERE id = ?", (estado, ahora(), identificador))
    conexion.commit()
    conexion.close()


def desc_todas():
    conexion = obt_conex()
    conexion.execute("UPDATE stations SET status = ?", ("DISCONNECTED",))
    conexion.commit()
    conexion.close()


def sumar_total(identificador, litros):  # Suma litros al total suministrado por la estación
    conexion = obt_conex()
    conexion.execute("UPDATE stations SET total = total + ? WHERE id = ?", (litros, identificador))
    conexion.commit()
    conexion.close()


def list_estac():
    conexion = obt_conex()
    filas = conexion.execute("SELECT * FROM stations ORDER BY id").fetchall()
    conexion.close()

    return [dict(fila) for fila in filas]


# Seguridad / Claves simétricas (P2)
def fij_clave(identificador, clave):  # Guarda la clave Fernet tras autenticación exitosa
    conexion = obt_conex()
    conexion.execute(
        """
        UPDATE stations
        SET registered = 1, authenticated = 1, symmetric_key = ?, key_status = 'ACTIVE', last_seen = ?
        WHERE id = ?
        """,
        (clave, ahora(), identificador),
    )
    conexion.commit()
    conexion.close()


def revocar_clave(identificador):  # Borra la clave simétrica y deja la WS fuera de servicio
    conexion = obt_conex()
    conexion.execute(
        """
        UPDATE stations
        SET authenticated = 0, symmetric_key = NULL, key_status = 'REVOKED', status = 'OUT_OF_SERVICE', last_seen = ?
        WHERE id = ?
        """,
        (ahora(), identificador),
    )
    conexion.commit()
    conexion.close()


# Clima y alertas (P2)
def act_clima(identificador, ciudad, temp_c, condicion, alerta, motivo=None, pending_stop=False):
    conexion = obt_conex()
    conexion.execute(
        """
        UPDATE stations
        SET city = ?, temp_c = ?, weather_condition = ?, weather_alert = ?,
            weather_reason = ?, weather_updated_at = ?, pending_weather_stop = ?
        WHERE id = ?
        """,
        (ciudad, temp_c, condicion, int(bool(alerta)), motivo, ahora(), int(bool(pending_stop)), identificador),
    )
    conexion.commit()
    conexion.close()


def limpiar_alerta(identificador):  # Cancela la alerta climática de una WS
    conexion = obt_conex()
    conexion.execute(
        """
        UPDATE stations
        SET weather_alert = 0, weather_reason = NULL, pending_weather_stop = 0, weather_updated_at = ?
        WHERE id = ?
        """,
        (ahora(), identificador),
    )
    conexion.commit()
    conexion.close()


# Auditoría (P2)
def reg_auditoria(source, actor, ip, action, level="INFO", details="", params=None):
    ts = ahora()
    params_json = json.dumps(params, ensure_ascii=False) if params is not None else None

    conexion = obt_conex()
    cursor = conexion.execute(
        """
        INSERT INTO audit_logs (timestamp, source, actor, ip, action, level, details, params)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (ts, source, actor, ip, action, level, details, params_json),
    )
    evento_id = cursor.lastrowid
    conexion.commit()
    conexion.close()

    # Persistencia estructurada adicional en fichero JSON Lines (un objeto JSON por línea)
    registro = {
        "id": evento_id,
        "timestamp": ts,
        "source": source,
        "actor": actor,
        "ip": ip,
        "action": action,
        "level": level,
        "details": details,
        "params": params,
    }
    try:
        with _audit_lock:
            with open(RUTA_AUDIT_JSONL, "a", encoding="utf-8") as f:
                f.write(json.dumps(registro, ensure_ascii=False) + "\n")
    except OSError:
        pass  # Un fallo al escribir el fichero no debe tumbar Central


def list_auditoria(limit=50, source=None, level=None, action=None, actor=None):  # Filtros parametrizados (anti SQLi)
    conexion = obt_conex()
    filtros = []
    params = []

    if source:
        filtros.append("source = ?")
        params.append(source)
    if level:
        filtros.append("level = ?")
        params.append(level)
    if action:
        filtros.append("action = ?")
        params.append(action)
    if actor:
        filtros.append("actor = ?")
        params.append(actor)

    consulta = "SELECT * FROM audit_logs"
    if filtros:
        consulta += " WHERE " + " AND ".join(filtros)
    consulta += " ORDER BY id DESC LIMIT ?"
    params.append(int(limit))

    filas = conexion.execute(consulta, params).fetchall()
    conexion.close()

    eventos = []
    for fila in filas:
        item = dict(fila)
        if item.get("params"):
            try:
                item["params"] = json.loads(item["params"])
            except ValueError:
                pass
        eventos.append(item)
    return eventos


# Auxiliar
def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")