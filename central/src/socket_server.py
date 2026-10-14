# socket_server.py
# Servidor de sockets de Central. Aquí se conectan los Monitores (WM_WS_M) de las estaciones.
# Cada Monitor abre UNA conexión que se mantiene abierta mientras la estación vive:
#   - Al conectar, se autentica (AUTH).
#   - Más tarde puede avisar de una fuga (LEAK) o de que se ha recuperado (RECOVERED).
#   - Si la conexión se cae, Central marca la estación como DESCONECTADA.
#
# Mensajes que entiende (campos separados por #):
#   AUTH#id#ubicacion   -> registra/autentica la estación
#   LEAK#id             -> la estación tiene una fuga
#   RECOVERED#id        -> la estación se ha recuperado
# Respuestas: "OK" o "KO#motivo"

import socket
import threading

from common import protocol
from src import state


def iniciar_servidor(puerto):
    """Abre el puerto y se queda esperando conexiones.
    Por cada Monitor que conecta, lanza un hilo para atenderlo.
    Esta función no termina nunca, así que hay que llamarla desde un hilo."""
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Permite reiniciar Central sin esperar a que el sistema libere el puerto
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind(("0.0.0.0", puerto))
    servidor.listen()

    print(f"[SOCKETS] Escuchando Monitores en el puerto {puerto}")

    while True:
        conexion, direccion = servidor.accept()
        print(f"[SOCKETS] Nueva conexión desde {direccion}")

        hilo = threading.Thread(
            target=atender_monitor,
            args=(conexion,),
            daemon=True
        )
        hilo.start()


def atender_monitor(conexion):
    """Atiende a un Monitor durante toda su conexión."""
    # Identificador de la estación de este Monitor. Hasta que se autentique es None.
    identificador_estacion = None

    try:
        # 1. El Monitor tiene que empezar con un ENQ
        tipo, contenido = protocol.recibir(conexion)

        if tipo != "CONTROL" or contenido != protocol.ENQ:
            conexion.sendall(protocol.NACK)
            return

        conexion.sendall(protocol.ACK)

        # 2. Bucle: recibir peticiones hasta que llegue EOT o se cierre la conexión
        while True:
            tipo, contenido = protocol.recibir(conexion)

            if tipo == "CONTROL" and contenido == protocol.EOT:
                break

            # Mensaje corrupto (LRC mal) o algo inesperado: pedimos que lo repita
            if tipo != "MESSAGE":
                conexion.sendall(protocol.NACK)
                continue

            # Mensaje correcto: lo confirmamos, lo procesamos y enviamos la respuesta
            conexion.sendall(protocol.ACK)

            respuesta, identificador_estacion = procesar_peticion(
                contenido,
                identificador_estacion
            )

            protocol.enviar_respuesta(conexion, respuesta)

    except (ConnectionError, OSError):
        # El Monitor ha cerrado o se ha caído la conexión
        pass

    finally:
        # Si la estación estaba autenticada, ahora queda desconectada
        if identificador_estacion is not None:
            state.establecer_estado(identificador_estacion, state.DISCONNECTED)
            print(f"[SOCKETS] {identificador_estacion} desconectada")

        conexion.close()


def procesar_peticion(texto, identificador_estacion):
    """Interpreta una petición del Monitor.
    Devuelve la respuesta y el identificador de la estación
    (que cambia al autenticarse)."""
    partes = texto.split(protocol.SEPARATOR)
    operacion = partes[0]

    # --- AUTH#id#ubicacion ---
    if operacion == "AUTH":
        if len(partes) < 3 or partes[1] == "":
            return "KO#Mensaje AUTH incorrecto", identificador_estacion

        nuevo_identificador = partes[1]
        ubicacion = partes[2]

        # Si esa estación ya está conectada con otro Monitor, rechazamos
        estado_actual = state.obtener_estado(nuevo_identificador)

        if estado_actual is not None and estado_actual != state.DISCONNECTED:
            return "KO#Estación ya conectada", identificador_estacion

        state.agregar_estacion(nuevo_identificador, ubicacion)
        state.establecer_estado(nuevo_identificador, state.ACTIVE)

        print(
            f"[SOCKETS] {nuevo_identificador} autenticada en '{ubicacion}'"
        )

        return "OK", nuevo_identificador

    # El resto de operaciones solo valen si el Monitor ya se ha autenticado
    if identificador_estacion is None:
        return "KO#No autenticado", identificador_estacion

    # --- LEAK#id y RECOVERED#id ---
    if operacion in ("LEAK", "RECOVERED"):
        if len(partes) < 2 or partes[1] != identificador_estacion:
            return "KO#Id incorrecto", identificador_estacion

        if operacion == "LEAK":
            state.establecer_estado(identificador_estacion, state.LEAK)
            print(
                f"[SOCKETS] AVERÍA en {identificador_estacion}: fuga detectada"
            )
        else:
            state.establecer_estado(identificador_estacion, state.ACTIVE)
            print(f"[SOCKETS] {identificador_estacion} recuperada")

        return "OK", identificador_estacion

    return "KO#Operación desconocida", identificador_estacion
