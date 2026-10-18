import os
import sys
import socket
import time
import threading

carpeta_raiz = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(carpeta_raiz)

from common.protocol.standard_lrc import StandardLRCProtocol
from common.protocol.line_delim import LineDelimitedProtocol

if len(sys.argv) < 3:
    print("Uso:python WM_WS_E.py <ip_kafka:puerto_kafka> <ip_monitor:puerto_monitor> [protocolo]")
    sys.exit(1)
try:
    # Estos tres son obligatorios: puerto del engine, ip:puerto de la central y id del WS
    dir_kafka, puerto_kafka = sys.argv[1].split(":")
    dir_monitor, puerto_monitor = sys.argv[2].split(":")
    puerto_kafka = int(puerto_kafka)
    puerto_monitor = int(puerto_monitor)
except ValueError:
    print("El puerto tiene que ser un número")
    sys.exit(1)

# Protocolo de sockets opcional: 'lrc' (por defecto) o 'line'
protocolo_nombre = "lrc"
if len(sys.argv) > 3:
    protocolo_nombre = sys.argv[3].lower()
protocol_class = StandardLRCProtocol if protocolo_nombre == "lrc" else LineDelimitedProtocol

id_ws = None
averia = False
protocol = protocol_class()

print(f"[ENGINE] Conectando al Monitor en {dir_monitor}:{puerto_monitor}...")
sock_monitor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock_monitor.connect((dir_monitor, puerto_monitor))

# Saludo inicial (ENQ -> ACK)
protocol.init_connection(sock_monitor)
print("[ENGINE] Conectado y listo para recibir comprobaciones de salud.")

def leer_teclado():
    global averia
    print(f"[{id_ws}] ⌨️  Pulsa 'k' + Enter para simular avería, 'r' + Enter para recuperar.")
    while True:
        try:
            linea = input()
            if "k" in linea.lower():
                averia = True
                print(f"[{id_ws}] Avería simulada activada (respondiendo KO)")
            elif "r" in linea.lower():
                averia = False
                print(f"[{id_ws}] Avería reparada (respondiendo OK)")
        except EOFError:
            break

try:
    while True:
        peticion = protocol.receive_request(sock_monitor)
        if peticion is None:
            print(f"[{id_ws or 'ENGINE'}] El Monitor ha cerrado la conexión.")
            break

        if peticion.startswith("CHECK_HEALTH"):
            # Si aún no sabíamos nuestro ID, lo extraemos de la trama CHECK_HEALTH#WS-01
            partes = peticion.split("#")
            if len(partes) > 1 and id_ws is None:
                id_ws = partes[1]
                print(f"[{id_ws}] ID asignado por el Monitor: {id_ws}")
                # Arrancamos el hilo del teclado una vez que conocemos nuestro ID
                threading.Thread(target=leer_teclado, daemon=True).start()

            # Respondemos OK o KO según el estado
            respuesta = "KO" if averia else "OK"
            protocol.send_response(sock_monitor, respuesta)

except KeyboardInterrupt:
    print(f"\n[{id_ws or 'ENGINE'}] Deteniendo Engine...")
finally:
    try:
        protocol.close_connection(sock_monitor)
    except Exception:
        pass
    sock_monitor.close()
    print(f"[{id_ws or 'ENGINE'}] Engine desconectado.")