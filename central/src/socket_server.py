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


def start_server(port):
    """Abre el puerto y se queda esperando conexiones.
    Por cada Monitor que conecta, lanza un hilo para atenderlo.
    Esta función no termina nunca, así que hay que llamarla desde un hilo."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Permite reiniciar Central sin esperar a que el sistema libere el puerto
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", port))
    server.listen()
    print(f"[SOCKETS] Escuchando Monitores en el puerto {port}")

    while True:
        conn, address = server.accept()
        print(f"[SOCKETS] Nueva conexión desde {address}")
        thread = threading.Thread(target=handle_monitor, args=(conn,), daemon=True)
        thread.start()


def handle_monitor(conn):
    """Atiende a un Monitor durante toda su conexión."""
    # Id de la estación de este Monitor. Hasta que se autentique es None.
    ws_id = None

    try:
        # 1. El Monitor tiene que empezar con un ENQ
        kind, content = protocol.receive(conn)
        if kind != "CONTROL" or content != protocol.ENQ:
            conn.sendall(protocol.NACK)
            return
        conn.sendall(protocol.ACK)

        # 2. Bucle: recibir peticiones hasta que llegue EOT o se cierre la conexión
        while True:
            kind, content = protocol.receive(conn)

            if kind == "CONTROL" and content == protocol.EOT:
                break

            # Mensaje corrupto (LRC mal) o algo inesperado: pedimos que lo repita
            if kind != "MESSAGE":
                conn.sendall(protocol.NACK)
                continue

            # Mensaje correcto: lo confirmamos, lo procesamos y enviamos la respuesta
            conn.sendall(protocol.ACK)
            answer, ws_id = process_request(content, ws_id)
            protocol.send_answer(conn, answer)

    except (ConnectionError, OSError):
        # El Monitor ha cerrado o se ha caído la conexión
        pass

    finally:
        # Si la estación estaba autenticada, ahora queda desconectada
        if ws_id is not None:
            state.set_status(ws_id, state.DISCONNECTED)
            print(f"[SOCKETS] {ws_id} desconectada")
        conn.close()


def process_request(text, ws_id):
    """Interpreta una petición del Monitor.
    Devuelve la respuesta y el id de la estación (que cambia al autenticarse)."""
    parts = text.split(protocol.SEPARATOR)
    operation = parts[0]

    # --- AUTH#id#ubicacion ---
    if operation == "AUTH":
        if len(parts) < 3 or parts[1] == "":
            return "KO#Mensaje AUTH incorrecto", ws_id

        new_id = parts[1]
        location = parts[2]

        # Si esa estación ya está conectada con otro Monitor, rechazamos
        current_status = state.get_status(new_id)
        if current_status is not None and current_status != state.DISCONNECTED:
            return "KO#Estación ya conectada", ws_id

        state.add_station(new_id, location)
        state.set_status(new_id, state.ACTIVE)
        print(f"[SOCKETS] {new_id} autenticada en '{location}'")
        return "OK", new_id

    # El resto de operaciones solo valen si el Monitor ya se ha autenticado
    if ws_id is None:
        return "KO#No autenticado", ws_id

    # --- LEAK#id y RECOVERED#id ---
    if operation in ("LEAK", "RECOVERED"):
        if len(parts) < 2 or parts[1] != ws_id:
            return "KO#Id incorrecto", ws_id

        if operation == "LEAK":
            state.set_status(ws_id, state.LEAK)
            print(f"[SOCKETS] AVERÍA en {ws_id}: fuga detectada")
        else:
            state.set_status(ws_id, state.ACTIVE)
            print(f"[SOCKETS] {ws_id} recuperada")
        return "OK", ws_id

    return "KO#Operación desconocida", ws_id