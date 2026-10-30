import os
import sys
import socket
import time
import threading

carpeta_raiz = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(carpeta_raiz)

from common.protocol.standard_lrc import StandardLRCProtocol
from common.protocol.line_delim import LineDelimitedProtocol

if len(sys.argv) < 4:
    print("Uso:python WM_WS_M.py <puerto_engine> <ip_central:puerto_central> <id_ws> [ubicacion] [protocolo]")
    sys.exit(1)
try:
    # Estos tres son obligatorios: puerto del engine, ip:puerto de la central y id del WS
    puerto = int(sys.argv[1])
    ip_central, puerto_central = sys.argv[2].split(":")
    id_ws = sys.argv[3]
    puerto_central = int(puerto_central)
except ValueError:
    print("El puerto tiene que ser un número")
    sys.exit(1)

# Argumentos opcionales: ubicación y protocolo de sockets
ubicacion = None
protocolo_nombre = "lrc"

if len(sys.argv) > 4:
    if sys.argv[4].lower() in ("lrc", "line"):
        protocolo_nombre = sys.argv[4].lower()
    else:
        ubicacion = sys.argv[4]

if len(sys.argv) > 5:
    protocolo_nombre = sys.argv[5].lower()
PROTOCOLS = {"lrc": StandardLRCProtocol, "line": LineDelimitedProtocol}
if protocolo_nombre not in PROTOCOLS:
    print(f"Error: Protocolo desconocido '{protocolo_nombre}'. Debe ser 'lrc' o 'line'.")
    sys.exit(1)
protocol_class = PROTOCOLS[protocolo_nombre]

lock_central = threading.Lock()  # Para sincronizar el acceso al socket de central

def enviar_a_central(mensaje):
    with lock_central:
        return protocol.send_request(sock_central, mensaje)


def vigilar_engine():
    protocol_engine = protocol_class()
    fuga_activa = False  # Para saber si ya hemos avisado a central o no

    while True:
        try:
            print(f"[{id_ws}] Esperando conexión del Engine...")
            conn_engine, addr = servidor_engine.accept()
            print(f"[{id_ws}] Engine conectado desde {addr}")

            # Saludo inicial con engine
            protocol_engine.accept_connection(conn_engine)

            while True:
                time.sleep(1)

                try:
                    # Le preguntamos a Engine como esta
                    estado = protocol_engine.send_request(conn_engine, f"CHECK_HEALTH#{id_ws}")
                except (ConnectionError, OSError, ValueError):
                    # Si se rompe el socket, se considera averia/fuga
                    estado = "KO"
                    conn_engine.close()

                # Caso 1: Engine reporta KO o se ha caído la conexión
                if estado == "KO":
                    if not fuga_activa:
                        print(f"[{id_ws}] ¡ALERTA! Fuga detectada en el Engine. Notificando a Central...")
                        enviar_a_central(f"LEAK#{id_ws}")
                        fuga_activa = True
                    # Si el socket se rompió, salimos para volver a esperar conexión
                    if conn_engine.fileno() == -1:
                        break
                # Caso 2: Engine está sano (OK)
                elif estado == "OK":
                    if fuga_activa:
                        print(f"[{id_ws}] Avería resuelta. Notificando recuperación a Central...")
                        enviar_a_central(f"RECOVERED#{id_ws}")
                        fuga_activa = False
        except Exception as e:
            time.sleep(1)   
                    


protocol = protocol_class()

print(f"[{id_ws}] Conectando a Central en {ip_central}:{puerto_central}...")
while True:
    try:
        sock_central = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock_central.connect((ip_central, puerto_central))
        protocol.init_connection(sock_central)
        break
    except (ConnectionError, OSError):
        sock_central.close()
        time.sleep(1)

peticion_alta = f"AUTH#{id_ws}#{ubicacion}" if ubicacion else f"AUTH#{id_ws}"
respuesta = protocol.send_request(sock_central, peticion_alta)

if respuesta == "OK":
    print(f"[{id_ws}] Autenticación correcta. Estación activa.")
else:
    print(f"[{id_ws}] Error al autenticar: {respuesta}")
    sock_central.close()
    sys.exit(1)

servidor_engine = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
servidor_engine.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
servidor_engine.bind(("0.0.0.0", puerto)) # Recuerda que 'puerto' es el puerto del Engine (sys.argv[1])
servidor_engine.listen(1)
print(f"[{id_ws}] Servidor local escuchando al Engine en el puerto {puerto}...")

hilo = threading.Thread(target=vigilar_engine, daemon=True)
hilo.start()

try:
    print(f"[{id_ws}] Monitor en ejecución. Pulsa Ctrl+C para finalizar.")

    while True:
        time.sleep(5)
        try:
            enviar_a_central("PING")
            # print(f"[{id_ws}] Ping enviado a Central (sesión viva)")
        except (ConnectionError, OSError):
            print(f"[{id_ws}] Conexión perdida con Central.")
            break
except KeyboardInterrupt:
    print(f"\n[{id_ws}] Desconectando de Central...")
finally:
    try:
        protocol.close_connection(sock_central)
    except Exception:
        pass
    sock_central.close()
    servidor_engine.close()
    print(f"[{id_ws}] Monitor cerrado.")
