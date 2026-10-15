# socket_server.py
# Servidor de sockets de Central. Aquí se conectan los Monitores (WM_WS_M) de las estaciones.
# Cada Monitor abre UNA conexión que se mantiene abierta mientras la estación está viva:
#   - Al conectar, se autentica con AUTH.
#   - Después puede avisar de una fuga (LEAK) o de que se ha recuperado (RECOVERED).
#   - Si la conexión se cae, Central pone la estación como DESCONECTADA.
#
# Mensajes que entiende (los campos van separados por #):
#   AUTH#id#ubicacion  -> registra/autentica la estación
#   LEAK#id            -> la estación tiene una fuga
#   RECOVERED#id       -> la estación se ha recuperado
# Respuestas posibles: "OK" o "KO#motivo"

import socket
import threading
import time

from common import protocol
from src import state


MAX_MON = 50        # Bulkhead: máximo de Monitores atendidos a la vez
TIEMPO_ESPERA = 5   # Timeout (s) para terminar un intercambio ya empezado
cupo = threading.BoundedSemaphore(MAX_MON)


def reg(texto):
    """Escribe una línea de log con la hora (observabilidad)."""
    print(time.strftime("%H:%M:%S"), texto)


def ini_servidor(puerto):
    """Abre el puerto y se queda esperando a que se conecten Monitores.
    Por cada Monitor que llega, crea un hilo para atenderlo.
    Esta función no termina nunca, así que se llama desde un hilo."""
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

        # Bulkhead: si ya hay demasiados Monitores, rechazamos la conexión
        if not cupo.acquire(blocking=False):
            reg("[SOCKETS] Demasiadas conexiones, se rechaza " + str(direccion))
            conexion.close()
            continue

        reg("[SOCKETS] Nueva conexión desde " + str(direccion))

        hilo = threading.Thread(target=atender_mon, args=(conexion,), daemon=True)
        hilo.start()


def atender_mon(conexion):
    """Atiende a un Monitor durante toda su conexión."""
    # Aquí guardamos el id de la estación de este Monitor.
    # Hasta que se autentique vale None.
    id_estacion = None

    try:
        # 1. Lo primero que debe llegar es un ENQ (con timeout)
        conexion.settimeout(TIEMPO_ESPERA)
        tipo, contenido = protocol.recib(conexion)

        if tipo != "CONTROL" or contenido != protocol.ENQ:
            conexion.sendall(protocol.NACK)
            return

        conexion.sendall(protocol.ACK)
        conexion.settimeout(None)

        # 2. Después recibimos peticiones hasta que llegue EOT o se cierre la conexión
        while True:
            tipo, contenido = protocol.recib(conexion)

            # Si llega EOT, el Monitor se despide
            if tipo == "CONTROL" and contenido == protocol.EOT:
                break

            # Si el mensaje llega mal (LRC incorrecto) o no es un mensaje, pedimos que lo repita
            if tipo != "MESSAGE":
                conexion.sendall(protocol.NACK)
                continue

            # Mensaje bien recibido: confirmamos, procesamos y contestamos
            # (con timeout: si el Monitor no confirma a tiempo, se corta)
            conexion.sendall(protocol.ACK)
            conexion.settimeout(TIEMPO_ESPERA)
            respuesta, id_estacion = proc_pet(contenido, id_estacion)
            protocol.env_resp(conexion, respuesta)
            conexion.settimeout(None)

    except (ConnectionError, OSError):
        # El Monitor se ha cerrado o se ha perdido la conexión
        pass

    finally:
        # Pase lo que pase, si la estación estaba autenticada pasa a DESCONECTADA
        if id_estacion is not None:
            state.fij_estado(id_estacion, state.DISCONNECTED)
            reg("[SOCKETS] " + id_estacion + " desconectada")

        conexion.close()
        cupo.release()


def proc_pet(texto, id_estacion):
    """Mira qué quiere el Monitor y le prepara la respuesta.
    Devuelve la respuesta y el id de la estación (que cambia cuando se autentica)."""
    partes = texto.split(protocol.SEPARATOR)
    operacion = partes[0]

    # --- AUTH#id#ubicacion ---
    if operacion == "AUTH":
        if len(partes) < 3 or partes[1] == "":
            return "KO#Mensaje AUTH incorrecto", id_estacion

        nuevo_id = partes[1]
        ubicacion = partes[2]

        # AUTH repetido en la misma conexión (p. ej. un reintento): es idempotente
        if nuevo_id == id_estacion:
            return "OK", id_estacion

        # Si la estación ya está conectada con otro Monitor, la rechazamos
        estado_actual = state.obt_estado(nuevo_id)
        if estado_actual is not None and estado_actual != state.DISCONNECTED:
            return "KO#Estación ya conectada", id_estacion

        state.alta_estac(nuevo_id, ubicacion)
        state.fij_estado(nuevo_id, state.ACTIVE)
        reg("[SOCKETS] " + nuevo_id + " autenticada en " + ubicacion)
        return "OK", nuevo_id

    # Las demás operaciones solo valen si el Monitor ya se ha autenticado
    if id_estacion is None:
        return "KO#No autenticado", id_estacion

    # --- LEAK#id  y  RECOVERED#id ---
    if operacion == "LEAK" or operacion == "RECOVERED":
        if len(partes) < 2 or partes[1] != id_estacion:
            return "KO#Id incorrecto", id_estacion

        if operacion == "LEAK":
            state.fij_estado(id_estacion, state.LEAK)
            reg("[SOCKETS] AVERÍA en " + id_estacion + ": fuga detectada")
        else:
            state.fij_estado(id_estacion, state.ACTIVE)
            reg("[SOCKETS] " + id_estacion + " recuperada")

        return "OK", id_estacion

    return "KO#Operación desconocida", id_estacion