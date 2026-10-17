import threading
import time

from database import db

# Estados posibles de una estación.
ACTIVE = "ACTIVE"                  # Disponible, esperando un riego (verde)
WATERING = "WATERING"              # Regando (verde parpadeando)
LEAK = "LEAK"                      # Fuga detectada (rojo)
OUT_OF_SERVICE = "OUT_OF_SERVICE"  # Parada por orden de Central (naranja)
DISCONNECTED = "DISCONNECTED"      # Sin conexión con Central (gris)

# Motivo que se da al operario cuando la estación no está disponible
MOTIVOS = {
    WATERING: "ya está regando",
    LEAK: "tiene una fuga",
    OUT_OF_SERVICE: "está fuera de servicio",
    DISCONNECTED: "está desconectada",
}

estaciones = {}

# lock para que dos hilos no modifiquen el diccionario a la vez
lock = threading.Lock()


def cargar_bd():  # Carga en memoria las estaciones de la BD (al arrancar)
    with lock:
        estaciones.clear()

        for fila in db.list_estac():
            estaciones[fila["id"]] = nueva_ent(fila["location"], fila["status"])


def nueva_ent(ubicacion, estado):  # Datos de una estación
    return {
        "location": ubicacion,
        "status": estado,
        "flow": 0,         # caudal actual
        "volume": 0,       # volumen acumulado en el riego en curso
        "operator": None,  # operario que ha pedido el riego en curso
        "start": None,     # hora de inicio del riego en curso
    }


def _resumen(ent, volumen):  # Resumen de un riego: operario, volumen y segundos que ha durado
    segundos = int(time.time() - ent["start"]) if ent["start"] else 0
    return {"operator": ent["operator"], "volume": volumen, "duration": segundos}


def _cambiar(identificador, estado):  # (interno, con el lock cogido) Cambia el estado y devuelve el resumen si cortaba un riego
    ent = estaciones[identificador]
    resumen = None

    if ent["status"] == WATERING and estado != WATERING:
        resumen = _resumen(ent, ent["volume"])

    ent["status"] = estado

    # Si deja de regar, ponemos a cero los datos del riego
    if estado != WATERING:
        ent["flow"] = 0
        ent["volume"] = 0
        ent["operator"] = None
        ent["start"] = None

    return resumen


def alta_estac(identificador, ubicacion):  # Añade una estación (o actualiza su ubicación) en la BD y en memoria
    db.reg_estac(identificador, ubicacion)

    with lock:
        if identificador in estaciones:
            estaciones[identificador]["location"] = ubicacion
        else:
            estaciones[identificador] = nueva_ent(ubicacion, DISCONNECTED)


def hay_estac(identificador):  # True si Central conoce esa estación
    with lock:
        return identificador in estaciones


def obt_estado(identificador):  # Estado de una estación (None si no existe)
    with lock:
        if identificador not in estaciones:
            return None

        return estaciones[identificador]["status"]


def es_disp(identificador):  # True solo si está ACTIVE
    return obt_estado(identificador) == ACTIVE


def fij_estado(identificador, estado):  # Cambia el estado (memoria + BD). Devuelve el resumen si cortaba un riego
    with lock:
        if identificador not in estaciones:
            return None

        resumen = _cambiar(identificador, estado)

    # La BD se actualiza fuera del lock para no bloquear a los demás hilos
    db.fij_estado(identificador, estado)
    return resumen


def cambiar_si(identificador, permitidos, estado):  # Cambia el estado solo si el actual está en 'permitidos'. Devuelve (cambiado, resumen)
    with lock:
        if identificador not in estaciones or estaciones[identificador]["status"] not in permitidos:
            return False, None

        resumen = _cambiar(identificador, estado)

    db.fij_estado(identificador, estado)
    return True, resumen


def res_riego(identificador, operario):  # Reserva la estación para un riego. Devuelve (True, None) o (False, motivo)
    with lock:
        if identificador not in estaciones:
            return False, "estación no registrada"

        ent = estaciones[identificador]

        if ent["status"] != ACTIVE:
            return False, MOTIVOS.get(ent["status"], "no está disponible")

        ent["status"] = WATERING
        ent["operator"] = operario
        ent["start"] = time.time()
        ent["flow"] = 0
        ent["volume"] = 0

    db.fij_estado(identificador, WATERING)
    return True, None


def act_riego(identificador, caudal, volumen):  # Actualiza el riego en curso (solo memoria). False si la estación no está regando
    with lock:
        if identificador not in estaciones or estaciones[identificador]["status"] != WATERING:
            return False

        estaciones[identificador]["flow"] = caudal
        estaciones[identificador]["volume"] = volumen
        return True


def fin_riego(identificador, volumen):  # Termina el riego: vuelve a ACTIVE y devuelve el resumen (None si no estaba regando)
    with lock:
        if identificador not in estaciones or estaciones[identificador]["status"] != WATERING:
            return None

        resumen = _resumen(estaciones[identificador], volumen)
        _cambiar(identificador, ACTIVE)

    db.fij_estado(identificador, ACTIVE)
    return resumen


def desc_todas():  # Pone todas las estaciones como desconectadas, en memoria y en la BD
    with lock:
        for identificador in estaciones:
            _cambiar(identificador, DISCONNECTED)

    db.desc_todas()


def obt_todas():  # Copia de todas las estaciones (para que el panel no pueda romper el original)
    with lock:
        return {identificador: dict(datos) for identificador, datos in estaciones.items()}