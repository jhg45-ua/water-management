import socket
import threading
import time

import sys
from pathlib import Path
# Añade la carpeta raíz (water-management) al path de Python
sys.path.append(str(Path(__file__).resolve().parents[1]))

from common.protocol.standard_lrc import StandardLRCProtocol

HOST = '127.0.0.1'
PORT = 9999

def run_server():
    """Función que ejecuta el servidor en un hilo separado."""
    protocol = StandardLRCProtocol()

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((HOST, PORT))
    server_sock.listen(1)

    print("[SERVIDOR] A la escucha en puerto 9999...")

    client_conn, client_addr = server_sock.accept()

    print(f"[SERVIDOR] Conexión aceptada desde {client_addr}")
    try:
        # Recibir petición
        request = protocol.receive_request(client_conn)
        print(f"[SERVIDOR] Petición recibida con éxito: '{request}'")
        # Responder
        response = "AUTH_OK#WS-01#Bienvenido"
        protocol.send_response(client_conn, response)
        print(f"[SERVIDOR] Respuesta enviada: '{response}'")
    finally:
        client_conn.close()
        server_sock.close()

def run_client():
    """Función que ejecuta el cliente."""
    time.sleep(0.2)  # Dar tiempo al servidor para arrancar
    protocol = StandardLRCProtocol()

    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_sock.connect((HOST, PORT))

    print("[CLIENTE] Conectado al servidor.")
    try:
        # Enviar petición y recibir respuesta
        peticion = "AUTH#WS-01#Parque Central"
        print(f"[CLIENTE] Enviando petición: '{peticion}'")
        respuesta = protocol.send_request(client_sock, peticion)
        print(f"[CLIENTE] Respuesta recibida del servidor: '{respuesta}'")
    finally:
        client_sock.close()

if __name__ == "__main__":
    # Ejecutamos el servidor en un hilo secundario y el cliente en otro
    hilo_servidor = threading.Thread(target=run_server)
    hilo_cliente = threading.Thread(target=run_client)
    hilo_servidor.start()
    hilo_cliente.start()
    hilo_servidor.join()
    hilo_cliente.join()
    print("\n✅ ¡Prueba completada con éxito!")