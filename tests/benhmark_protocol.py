import socket
import threading
import time

import sys
from pathlib import Path
# Añade la carpeta raíz (water-management) al path de Python
sys.path.append(str(Path(__file__).resolve().parents[1]))

from common.protocol.standard_lrc import StandardLRCProtocol

HOST = "127.0.0.1"
PORT = 9998
NUM_REQUESTS = 500  # Número de mensajes a medir

def run_server():
    protocol = StandardLRCProtocol()
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((HOST, PORT))
    server_sock.listen(1)

    client_conn, _ = server_sock.accept()
    try:
        # Atendemos NUM_REQUESTS peticiones sobre la misma conexión
        for _ in range(NUM_REQUESTS):
            request = protocol.receive_request(client_conn)
            protocol.send_response(client_conn, "AUTH_OK#WS-01#Bienvenido")
    finally:
        client_conn.close()
        server_sock.close()

def run_client():
    time.sleep(0.2)  # Espera para que el servidor arranque
    protocol = StandardLRCProtocol()
    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_sock.connect((HOST, PORT))

    try:
        print(f"⏱️  Iniciando benchmark con {NUM_REQUESTS} peticiones...")
        t_inicio = time.perf_counter()

        for i in range(NUM_REQUESTS):
            mensaje = f"AUTH#WS-{i:03d}#Parque Central"
            _ = protocol.send_request(client_sock, mensaje)

        t_fin = time.perf_counter()
        t_total = t_fin - t_inicio
        latencia_media_ms = (t_total / NUM_REQUESTS) * 1000
        ops_por_segundo = NUM_REQUESTS / t_total

        print("\n================ RESULTADOS (Protocolo LRC) ================")
        print(f" Peticiones procesadas:    {NUM_REQUESTS}")
        print(f" Tiempo total:             {t_total:.4f} segundos")
        print(f" Latencia media / pet:     {latencia_media_ms:.4f} ms")
        print(f" Rendimiento (Throughput): {ops_por_segundo:.2f} peticiones/seg")
        print("===========================================================\n")
    finally:
        client_sock.close()

if __name__ == "__main__":
    t_server = threading.Thread(target=run_server)
    t_client = threading.Thread(target=run_client)

    t_server.start()
    t_client.start()

    t_server.join()
    t_client.join()