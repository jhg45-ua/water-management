# state.py
# Aquí guardamos el estado EN VIVO de todas las estaciones de riego.
# La base de datos guarda lo que debe sobrevivir a un reinicio; este fichero guarda
# lo que cambia cada segundo (estado, caudal, volumen...) y lo que lee el panel.
#
# Central tiene varios hilos (sockets, Kafka, panel) que leen y escriben aquí
# a la vez, así que todo se protege con un Lock para que no se pisen.

import threading

from database import db

# Estados posibles de una estación. Son los mismos textos que se guardan en la BD.
ACTIVE = "ACTIVE"                  # Disponible, esperando un riego (verde)
WATERING = "WATERING"              # Regando (verde parpadeando)
LEAK = "LEAK"                      # Fuga detectada (rojo)
OUT_OF_SERVICE = "OUT_OF_SERVICE"  # Parada por orden de Central (naranja)
DISCONNECTED = "DISCONNECTED"      # Sin conexión con Central (gris)

# Diccionario con todas las estaciones. La clave es el identificador de la estación.
# Ejemplo: estaciones["WS01"] = {"location": "...", "status": "ACTIVE", ...}
estaciones = {}

# lock para que dos hilos no modifiquen el diccionario a la vez
lock = threading.Lock()


def cargar_desde_bd():
    """Carga en memoria las estaciones que hay guardadas en la BD.
    Se llama al arrancar Central, después de marcarlas como desconectadas."""
    with lock:
        estaciones.clear()

        for fila in db.listar_estaciones():
            estaciones[fila["id"]] = crear_entrada(
                fila["location"],
                fila["status"]
            )


def crear_entrada(ubicacion, estado):
    """Crea los datos de una estación. Es un auxiliar para no repetir el diccionario."""
    return {
        "location": ubicacion,
        "status": estado,
        "flow": 0,         # caudal actual
        "volume": 0,       # volumen acumulado en el riego en curso
        "operator": None,  # operario que ha pedido el riego en curso
    }


def agregar_estacion(identificador, ubicacion):
    """Añade una estación nueva (o actualiza su ubicación si ya estaba).
    Se usa cuando un Monitor se autentica: la guarda en la BD y en memoria."""
    db.registrar_estacion(identificador, ubicacion)

    with lock:
        if identificador in estaciones:
            estaciones[identificador]["location"] = ubicacion
        else:
            estaciones[identificador] = crear_entrada(
                ubicacion,
                DISCONNECTED
            )


def existe_estacion(identificador):
    """Devuelve True si Central conoce esa estación."""
    with lock:
        return identificador in estaciones


def obtener_estado(identificador):
    """Devuelve el estado de una estación, o None si no existe."""
    with lock:
        if identificador not in estaciones:
            return None

        return estaciones[identificador]["status"]


def esta_disponible(identificador):
    """Una estación está disponible para regar solo si está ACTIVA:
    ni regando, ni con fuga, ni parada, ni desconectada."""
    return obtener_estado(identificador) == ACTIVE


def establecer_estado(identificador, estado):
    """Cambia el estado de una estación, en memoria y en la BD."""
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
    db.establecer_estado(identificador, estado)


def actualizar_riego(identificador, operario, caudal, volumen):
    """Actualiza los datos de un riego en curso (llega cada segundo desde la estación).
    Solo toca la memoria; no escribimos en la BD cada segundo."""
    with lock:
        if identificador not in estaciones:
            return

        estaciones[identificador]["status"] = WATERING
        estaciones[identificador]["operator"] = operario
        estaciones[identificador]["flow"] = caudal
        estaciones[identificador]["volume"] = volumen


def desconectar_todas_estaciones():
    """Pone todas las estaciones como desconectadas, en memoria y en la BD."""
    with lock:
        for identificador in estaciones:
            estaciones[identificador]["status"] = DISCONNECTED
            estaciones[identificador]["flow"] = 0
            estaciones[identificador]["volume"] = 0
            estaciones[identificador]["operator"] = None

    db.desconectar_todas_estaciones()


def obtener_todas():
    """Devuelve una copia de todas las estaciones.
    Es una copia para que quien la lea (el panel) no pueda romper el original."""
    with lock:
        resultado = {}

        for identificador, datos in estaciones.items():
            resultado[identificador] = dict(datos)

        return resultado
