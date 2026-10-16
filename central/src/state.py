import threading

from database import db

# Estados posibles de una estación.
ACTIVE = "ACTIVE"                  # Disponible, esperando un riego (verde)
WATERING = "WATERING"              # Regando (verde parpadeando)
LEAK = "LEAK"                      # Fuga detectada (rojo)
OUT_OF_SERVICE = "OUT_OF_SERVICE"  # Parada por orden de Central (naranja)
DISCONNECTED = "DISCONNECTED"      # Sin conexión con Central (gris)


estaciones = {}

# lock para que dos hilos no modifiquen el diccionario a la vez
lock = threading.Lock()


def cargar_bd():
    with lock:
        estaciones.clear()

        for fila in db.list_estac():
            estaciones[fila["id"]] = nueva_ent(
                fila["location"],
                fila["status"]
            )

#AUXILIAR:Datos de una estacion
def nueva_ent(ubicacion, estado):
    return {
        "location": ubicacion,
        "status": estado,
        "flow": 0,         # caudal actual
        "volume": 0,       # volumen acumulado en el riego en curso
        "operator": None,  # operario que ha pedido el riego en curso
    }


def alta_estac(identificador, ubicacion):
    db.reg_estac(identificador, ubicacion)

    with lock:
        if identificador in estaciones:
            estaciones[identificador]["location"] = ubicacion
        else:
            estaciones[identificador] = nueva_ent(
                ubicacion,
                DISCONNECTED
            )


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
            return

        estaciones[identificador]["status"] = estado

        # Si deja de regar, ponemos a cero los datos del riego
        if estado != WATERING:
            estaciones[identificador]["flow"] = 0
            estaciones[identificador]["volume"] = 0
            estaciones[identificador]["operator"] = None

    # La BD se actualiza fuera del lock para no bloquear a los demás hilos
    db.fij_estado(identificador, estado)


def act_riego(identificador, operario, caudal, volumen):
    with lock:
        if identificador not in estaciones:
            return

        estaciones[identificador]["status"] = WATERING
        estaciones[identificador]["operator"] = operario
        estaciones[identificador]["flow"] = caudal
        estaciones[identificador]["volume"] = volumen


def desc_todas():
    """Pone todas las estaciones como desconectadas, en memoria y en la BD."""
    with lock:
        for identificador in estaciones:
            estaciones[identificador]["status"] = DISCONNECTED
            estaciones[identificador]["flow"] = 0
            estaciones[identificador]["volume"] = 0
            estaciones[identificador]["operator"] = None

    db.desc_todas()


def obt_todas():
    """Devuelve una copia de todas las estaciones.
    Es una copia para que quien la lea (el panel) no pueda romper el original."""
    with lock:
        resultado = {}

        for identificador, datos in estaciones.items():
            resultado[identificador] = dict(datos)

        return resultado