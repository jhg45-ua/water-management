import threading
import time

from database import db


ACTIVE = "ACTIVE"
WATERING = "WATERING"
LEAK = "LEAK"
OUT_OF_SERVICE = "OUT_OF_SERVICE"
DISCONNECTED = "DISCONNECTED"

MOTIVOS = {
    WATERING: "ya está regando",
    LEAK: "tiene una fuga",
    OUT_OF_SERVICE: "está fuera de servicio",
    DISCONNECTED: "está desconectada",
}

estaciones = {}

lock = threading.Lock()


def cargar_bd():
    with lock:
        estaciones.clear()

        for fila in db.list_estac():
            estaciones[fila["id"]] = nueva_ent(fila["location"], fila["status"], fila.get("total") or 0)


def nueva_ent(ubicacion, estado, total=0):
    return {
        "location": ubicacion,
        "status": estado,
        "flow": 0,
        "volume": 0,
        "operator": None,
        "start": None,
        "total": total,
    }


def _cambiar(identificador, estado):
    ent = estaciones[identificador]
    resumen = None

    if ent["status"] == WATERING and estado != WATERING:
        segundos = int(time.time() - ent["start"]) if ent["start"] else 0
        resumen = {"operator": ent["operator"], "volume": ent["volume"], "duration": segundos}
        ent["total"] += ent["volume"]

    ent["status"] = estado

    if estado != WATERING:
        ent["flow"] = 0
        ent["volume"] = 0
        ent["operator"] = None
        ent["start"] = None

    return resumen


def alta_estac(identificador, ubicacion):
    db.reg_estac(identificador, ubicacion)

    with lock:
        if identificador in estaciones:
            estaciones[identificador]["location"] = ubicacion
        else:
            estaciones[identificador] = nueva_ent(ubicacion, DISCONNECTED)


def hay_estac(identificador):
    with lock:
        return identificador in estaciones


def obt_estado(identificador):
    with lock:
        if identificador not in estaciones:
            return None

        return estaciones[identificador]["status"]


def es_disp(identificador):
    return obt_estado(identificador) == ACTIVE


def fij_estado(identificador, estado):
    with lock:
        if identificador not in estaciones:
            return None

        resumen = _cambiar(identificador, estado)

    # Actualizamos la BD fuera del lock para no bloquear otros hilos.
    db.fij_estado(identificador, estado)

    if resumen:
        db.sumar_total(identificador, resumen["volume"])

    return resumen


def cambiar_si(identificador, permitidos, estado):
    with lock:
        if identificador not in estaciones or estaciones[identificador]["status"] not in permitidos:
            return False, None

        resumen = _cambiar(identificador, estado)

    db.fij_estado(identificador, estado)

    if resumen:
        db.sumar_total(identificador, resumen["volume"])

    return True, resumen


def res_riego(identificador, operario):
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


def act_riego(identificador, caudal, volumen):
    with lock:
        if identificador not in estaciones or estaciones[identificador]["status"] != WATERING:
            return False

        estaciones[identificador]["flow"] = caudal
        estaciones[identificador]["volume"] = volumen
        return True


def fin_riego(identificador, volumen):
    with lock:
        if identificador not in estaciones or estaciones[identificador]["status"] != WATERING:
            return None

        estaciones[identificador]["volume"] = volumen
        resumen = _cambiar(identificador, ACTIVE)

    db.fij_estado(identificador, ACTIVE)
    db.sumar_total(identificador, resumen["volume"])
    return resumen


def desc_todas():
    with lock:
        for identificador in estaciones:
            _cambiar(identificador, DISCONNECTED)

    db.desc_todas()


def obt_todas():
    with lock:
        return {identificador: dict(datos) for identificador, datos in estaciones.items()}