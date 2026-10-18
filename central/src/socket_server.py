import socket
import threading
import time
import os

from common.protocol.standard_lrc import StandardLRCProtocol
from common.protocol.line_delim import LineDelimitedProtocol
from src import state
from src import kafka_handlers

SEPARATOR = "#"

PROTOCOLS = {
    "lrc": StandardLRCProtocol,
    "line": LineDelimitedProtocol
}

MAX_MON = 50
TIEMPO_ESPERA = 5
TIEMPO_VIDA = int(os.environ.get("TIEMPO_VIDA", 15))  # segundos sin noticias del Monitor = caído (0 = desactivado)
ESPERA_VIDA = TIEMPO_VIDA or None
cupo = threading.BoundedSemaphore(MAX_MON)


def reg(texto):
    print(time.strftime("%H:%M:%S"), texto)


def ini_servidor(puerto, protocol_class=StandardLRCProtocol):
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        servidor.bind(("0.0.0.0", puerto))
    except OSError:
        reg("[SOCKETS] No se puede abrir el puerto " + str(puerto) + " (¿ya está en uso?)")
        return

    servidor.listen()
    reg("[SOCKETS] Escuchando Monitores en el puerto " + str(puerto))

    while True:
        conexion, direccion = servidor.accept()

        if not cupo.acquire(blocking=False):
            reg("[SOCKETS] Demasiadas conexiones, se rechaza " + str(direccion))
            conexion.close()
            continue

        reg("[SOCKETS] Nueva conexión desde " + str(direccion))

        hilo = threading.Thread(target=atender_mon, args=(conexion, protocol_class), daemon=True)
        hilo.start()


def atender_mon(conexion, protocol_class=StandardLRCProtocol):
    id_estacion = None
    protocol = protocol_class()

    try:
        conexion.settimeout(ESPERA_VIDA)
        protocol.accept_connection(conexion)
        conexion.settimeout(ESPERA_VIDA)

        while True:
            peticion = protocol.receive_request(conexion)

            if peticion is None:
                break

            conexion.settimeout(TIEMPO_ESPERA)
            respuesta, id_estacion = proc_pet(peticion, id_estacion)
            protocol.send_response(conexion, respuesta)
            conexion.settimeout(None)

    except (ConnectionError, OSError, ValueError):
        pass

    finally:
        if id_estacion is not None:
            kafka_handlers.estacion_desconectada(id_estacion)
            reg("[SOCKETS] " + id_estacion + " desconectada")

        conexion.close()
        cupo.release()


def proc_pet(texto, id_estacion):
    partes = texto.split(SEPARATOR)
    operacion = partes[0]

    # PING : mensaje de vida del Monitor (que llegue ya basta para saber que sigue vivo)
    if operacion == "PING":
        return "OK", id_estacion

    # REGISTER#id#ubicacion : da de alta una estación nueva (o actualiza su ubicación)
    if operacion == "REGISTER":
        if len(partes) < 3 or partes[1] == "":
            return "KO#Mensaje REGISTER incorrecto", id_estacion

        state.alta_estac(partes[1], partes[2])
        reg("[SOCKETS] " + partes[1] + " registrada en " + partes[2])
        return "OK", id_estacion

    # AUTH#id (estricta: la estación debe estar registrada) o AUTH#id#ubicacion (la registra si hace falta)
    if operacion == "AUTH":
        if len(partes) < 2 or partes[1] == "":
            return "KO#Mensaje AUTH incorrecto", id_estacion

        nuevo_id = partes[1]

        # AUTH repetido en la misma conexión (p. ej. un reintento)
        if nuevo_id == id_estacion:
            return "OK", id_estacion

        # Si la estación ya está conectada con otro Monitor, la rechazo
        estado_actual = state.obt_estado(nuevo_id)
        if estado_actual is not None and estado_actual != state.DISCONNECTED:
            return "KO#Estación ya conectada", id_estacion

        if len(partes) >= 3:
            state.alta_estac(nuevo_id, partes[2])
        elif estado_actual is None:
            return "KO#WS no registrada", id_estacion

        state.fij_estado(nuevo_id, state.ACTIVE)
        reg("[SOCKETS] " + nuevo_id + " autenticada")
        return "OK", nuevo_id

    if id_estacion is None:
        return "KO#No autenticado", id_estacion

    # LEAK#id y RECOVERED#id
    if operacion == "LEAK" or operacion == "RECOVERED":
        if len(partes) < 2 or partes[1] != id_estacion:
            return "KO#Id incorrecto", id_estacion

        if operacion == "LEAK":
            kafka_handlers.estacion_con_fuga(id_estacion)
            reg("[SOCKETS] AVERÍA en " + id_estacion + ": fuga detectada")
        else:
            state.cambiar_si(id_estacion, (state.LEAK,), state.ACTIVE)
            reg("[SOCKETS] " + id_estacion + " recuperada")

        return "OK", id_estacion

    return "KO#Operación desconocida", id_estacion