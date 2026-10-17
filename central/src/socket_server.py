import socket
import threading
import time

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
cupo = threading.BoundedSemaphore(MAX_MON)

#Escribe una línea de log con la hora (observabilidad).
def reg(texto):
    print(time.strftime("%H:%M:%S"), texto)


#Abre puerto , espera a que lleguen y si llega crea hilo
def ini_servidor(puerto, protocol_class=StandardLRCProtocol):
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Esto permite reiniciar Central sin esperar a que se libere el puerto
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Si el puerto ya está ocupado, avisamos y salimos
    try:
        servidor.bind(("0.0.0.0", puerto))
    except OSError:
        reg("[SOCKETS] No se puede abrir el puerto " + str(puerto) + " (¿ya está en uso?)")
        return

    servidor.listen()
    reg("[SOCKETS] Escuchando Monitores en el puerto " + str(puerto))

    while True:
        conexion, direccion = servidor.accept()

      #Si hubiesen muchos monitones
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
        # 1.ENQ
        conexion.settimeout(TIEMPO_ESPERA)
        # tipo, contenido = protocol.recib(conexion)
        protocol.accept_connection(conexion)

        # if tipo != "CONTROL" or contenido != protocol.ENQ:
        #     conexion.sendall(protocol.NACK)
        #     return

        # conexion.sendall(protocol.ACK)
        conexion.settimeout(None)

        # 2.Recibir peticiones hasta EOT o se cierre la conexión
        while True:
            # tipo, contenido = protocol.recib(conexion)
            peticion = protocol.receive_request(conexion)

            if peticion is None:
                # El cliente ha enviado EOT (fin de comunicación) o ha cerrado
                break

            # Si llega EOT, el Monitor se despide
            # if tipo == "CONTROL" and contenido == protocol.EOT:
            #     break

            # Si el mensaje llega mal (LRC incorrecto) o no es un mensaje, pedimos que lo repita
            # if tipo != "MESSAGE":
            #     conexion.sendall(protocol.NACK)
            #     continue

            # Mensaje bien recibido: confirmamos, procesamos y contestamos
            # conexion.sendall(protocol.ACK)
            conexion.settimeout(TIEMPO_ESPERA)
            respuesta, id_estacion = proc_pet(peticion, id_estacion)
            # protocol.env_resp(conexion, respuesta)
            protocol.send_response(conexion, respuesta)
            conexion.settimeout(None)

    except (ConnectionError, OSError,ValueError):
        pass

    finally:
        if id_estacion is not None:
            kafka_handlers.estacion_desconectada(id_estacion)
            reg("[SOCKETS] " + id_estacion + " desconectada")

        conexion.close()
        cupo.release()

#Prepara respuesta
def proc_pet(texto, id_estacion):
    partes = texto.split(SEPARATOR)
    operacion = partes[0]

    #AUTH#id#ubicacion
    if operacion == "AUTH":
        if len(partes) < 3 or partes[1] == "":
            return "KO#Mensaje AUTH incorrecto", id_estacion

        nuevo_id = partes[1]
        ubicacion = partes[2]

        # AUTH
        if nuevo_id == id_estacion:
            return "OK", id_estacion

        # Si la estación ya está conectada con otro Monitor, la rechazo
        estado_actual = state.obt_estado(nuevo_id)
        if estado_actual is not None and estado_actual != state.DISCONNECTED:
            return "KO#Estación ya conectada", id_estacion

        state.alta_estac(nuevo_id, ubicacion)
        state.fij_estado(nuevo_id, state.ACTIVE)
        reg("[SOCKETS] " + nuevo_id + " autenticada en " + ubicacion)
        return "OK", nuevo_id
    
    if id_estacion is None:
        return "KO#No autenticado", id_estacion

    #LEAK#id  y  RECOVERED#id
    if operacion == "LEAK" or operacion == "RECOVERED":
        if len(partes) < 2 or partes[1] != id_estacion:
            return "KO#Id incorrecto", id_estacion

        if operacion == "LEAK":
            kafka_handlers.estacion_con_fuga(id_estacion)
            reg("[SOCKETS] AVERÍA en " + id_estacion + ": fuga detectada")
        else:
            state.fij_estado(id_estacion, state.ACTIVE)
            reg("[SOCKETS] " + id_estacion + " recuperada")

        return "OK", id_estacion

    return "KO#Operación desconocida", id_estacion