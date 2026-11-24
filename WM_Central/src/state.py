import hashlib
import threading
import time
from datetime import datetime

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


def _fingerprint(clave):  # Huella corta de la clave simétrica para mostrar en el Front sin exponerla
    if not clave:
        return None
    return hashlib.sha256(clave.encode("utf-8")).hexdigest()[:8]


def _iso_ahora():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def cargar_bd():
    with lock:
        estaciones.clear()

        for fila in db.list_estac():
            ent = nueva_ent(fila["location"], fila["status"], fila.get("total") or 0)
            ent["registered"] = bool(fila.get("registered"))
            ent["authenticated"] = bool(fila.get("authenticated"))
            ent["symmetric_key"] = fila.get("symmetric_key")
            ent["key_status"] = fila.get("key_status") or "NONE"
            ent["pending_weather_stop"] = bool(fila.get("pending_weather_stop"))
            ent["last_seen"] = fila.get("last_seen")
            ent["weather"] = {
                "city": fila.get("city") or fila["location"],
                "temp_c": fila.get("temp_c"),
                "condition": fila.get("weather_condition"),
                "alert": bool(fila.get("weather_alert")),
                "reason": fila.get("weather_reason"),
                "updated_at": fila.get("weather_updated_at"),
            }
            estaciones[fila["id"]] = ent


def nueva_ent(ubicacion, estado, total=0):
    return {
        "location": ubicacion,
        "status": estado,
        "flow": 0,
        "volume": 0,
        "operator": None,
        "start": None,
        "total": total,
        "registered": False,
        "authenticated": False,
        "symmetric_key": None,
        "key_status": "NONE",
        "pending_weather_stop": False,
        "last_seen": _iso_ahora(),
        "weather": {
            "city": ubicacion,
            "temp_c": None,
            "condition": None,
            "alert": False,
            "reason": None,
            "updated_at": None,
        },
    }


def _cambiar(identificador, estado):
    ent = estaciones[identificador]
    resumen = None

    if ent["status"] == WATERING and estado != WATERING:
        segundos = int(time.time() - ent["start"]) if ent["start"] else 0
        resumen = {"operator": ent["operator"], "volume": ent["volume"], "duration": segundos}
        ent["total"] += ent["volume"]

    ent["status"] = estado
    ent["last_seen"] = _iso_ahora()

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
            if not estaciones[identificador]["weather"]["city"]:
                estaciones[identificador]["weather"]["city"] = ubicacion
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

        if ent["weather"]["alert"]:
            return False, f"alerta climática activa ({ent['weather']['reason'] or 'clima adverso'})"

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

        ent = estaciones[identificador]
        ent["volume"] = volumen
        # Si llegó una alerta climática durante el riego, al acabar pasa a OUT_OF_SERVICE
        bloquear_por_clima = ent["pending_weather_stop"] or ent["weather"]["alert"]
        nuevo_estado = OUT_OF_SERVICE if bloquear_por_clima else ACTIVE
        ent["pending_weather_stop"] = False

        resumen = _cambiar(identificador, nuevo_estado)
        resumen["blocked_by_weather"] = bloquear_por_clima

    db.fij_estado(identificador, nuevo_estado)
    db.sumar_total(identificador, resumen["volume"])
    if bloquear_por_clima:
        w = estaciones[identificador]["weather"]
        db.act_clima(identificador, w["city"], w["temp_c"], w["condition"], True, w["reason"], pending_stop=False)
    return resumen


def desc_todas():
    with lock:
        for identificador in estaciones:
            _cambiar(identificador, DISCONNECTED)

    db.desc_todas()


# Gestión de claves simétricas (P2)
def fij_clave(identificador, clave):
    with lock:
        if identificador not in estaciones:
            return False
        ent = estaciones[identificador]
        ent["registered"] = True
        ent["authenticated"] = True
        ent["symmetric_key"] = clave
        ent["key_status"] = "ACTIVE"
        ent["last_seen"] = _iso_ahora()

    db.fij_clave(identificador, clave)
    return True


def revocar_clave(identificador):
    with lock:
        if identificador not in estaciones:
            return False
        ent = estaciones[identificador]
        ent["authenticated"] = False
        ent["symmetric_key"] = None
        ent["key_status"] = "REVOKED"
        _cambiar(identificador, OUT_OF_SERVICE)

    db.revocar_clave(identificador)
    return True


def obt_clave(identificador):
    with lock:
        ent = estaciones.get(identificador)
        return ent["symmetric_key"] if ent else None


# Gestión de clima y alertas (P2)
def aplicar_clima(identificador, ciudad, temp_c, condicion, alerta, motivo=None):
    send_block = False
    cambio_estado = None

    with lock:
        if identificador not in estaciones:
            return None

        ent = estaciones[identificador]
        alerta = bool(alerta)
        ent["weather"] = {
            "city": ciudad,
            "temp_c": temp_c,
            "condition": condicion,
            "alert": alerta,
            "reason": motivo if alerta else None,
            "updated_at": _iso_ahora(),
        }

        if alerta:
            if ent["status"] == WATERING:
                ent["pending_weather_stop"] = True
            elif ent["status"] == ACTIVE:
                _cambiar(identificador, OUT_OF_SERVICE)
                ent["pending_weather_stop"] = False
                cambio_estado = OUT_OF_SERVICE
                send_block = True
        else:
            ent["pending_weather_stop"] = False

        resultado = {
            "ws_id": identificador,
            "weather_alert": alerta,
            "status": ent["status"],
            "pending_weather_stop": ent["pending_weather_stop"],
            "send_block": send_block,
        }

    db.act_clima(identificador, ciudad, temp_c, condicion, alerta, motivo if alerta else None, resultado["pending_weather_stop"])
    if cambio_estado:
        db.fij_estado(identificador, cambio_estado)

    return resultado


def cancelar_alerta_clima(identificador):
    send_activate = False
    cambio_estado = None

    with lock:
        if identificador not in estaciones:
            return None

        ent = estaciones[identificador]
        ent["weather"]["alert"] = False
        ent["weather"]["reason"] = None
        ent["weather"]["updated_at"] = _iso_ahora()
        ent["pending_weather_stop"] = False

        # Solo restauramos si estaba fuera de servicio y no tiene la clave revocada
        if ent["status"] == OUT_OF_SERVICE and ent["key_status"] != "REVOKED":
            _cambiar(identificador, ACTIVE)
            cambio_estado = ACTIVE
            send_activate = True

        resultado = {
            "ws_id": identificador,
            "weather_alert": False,
            "status": ent["status"],
            "send_activate": send_activate,
        }

    db.limpiar_alerta(identificador)
    if cambio_estado:
        db.fij_estado(identificador, cambio_estado)

    return resultado


# Lectura de estado (P1 y contrato API_Central P2)
def obt_todas():
    with lock:
        return {identificador: dict(datos) for identificador, datos in estaciones.items()}


def _serializar_api(identificador, ent):  # Formato del contrato GET /api/stations (sin exponer symmetric_key)
    return {
        "ws_id": identificador,
        "location": ent["location"],
        "status": ent["status"],
        "registered": ent["registered"],
        "authenticated": ent["authenticated"],
        "key_status": ent["key_status"],
        "key_fingerprint": _fingerprint(ent["symmetric_key"]),
        "flow": ent["flow"],
        "volume": ent["volume"],
        "total": ent["total"],
        "operator": ent["operator"],
        "pending_weather_stop": ent["pending_weather_stop"],
        "weather": dict(ent["weather"]),
        "last_seen": ent["last_seen"],
    }


def obt_estacion_api(identificador):
    with lock:
        ent = estaciones.get(identificador)
        return _serializar_api(identificador, ent) if ent else None


def obt_todas_api():
    with lock:
        return [_serializar_api(ws_id, ent) for ws_id, ent in sorted(estaciones.items())]


def obt_riegos_api():
    with lock:
        riegos = []
        for ws_id, ent in sorted(estaciones.items()):
            if ent["status"] == WATERING:
                started = datetime.utcfromtimestamp(ent["start"]).strftime("%Y-%m-%dT%H:%M:%SZ") if ent["start"] else None
                riegos.append({
                    "ws_id": ws_id,
                    "operator_id": ent["operator"],
                    "flow": ent["flow"],
                    "volume": ent["volume"],
                    "started_at": started,
                })
        return riegos