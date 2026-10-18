import os
import sys
import threading
import time

carpeta_raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(carpeta_raiz)

from database import db
from src import state
from src import socket_server
from src import kafka_handlers
from src import commands
from src.panel import app as panel


# Operarios que se dan de alta al arrancar. Si hace falta alguno más, se añade aquí.
operarios = [("OP01", "Operario 1"), ("OP02", "Operario 2"), ("OP03", "Operario 3")]

#PARÁMETROS

if len(sys.argv) < 2:
    print("Uso:python WM_Central.py <puerto> [ip_kafka:puerto_kafka] [ruta_bd]")
    sys.exit(1)

try:
    puerto = int(sys.argv[1])
except ValueError:
    print("El puerto tiene que ser un número")
    sys.exit(1)

direccion_kafka = sys.argv[2] if len(sys.argv) > 2 else "localhost:9092"
ruta_bd = sys.argv[3] if len(sys.argv) > 3 else None
# Protocolo de sockets opcional: 'lrc' (por defecto) o 'line'
protocolo_nombre = sys.argv[4].lower() if len(sys.argv) > 4 else "lrc"
protocol_class = socket_server.PROTOCOLS.get(protocolo_nombre, socket_server.StandardLRCProtocol)
print(f"[CENTRAL] Protocolo de sockets seleccionado: '{protocol_class.__name__}'")
#BASE DE DATOS Y EL ESTADO

print("[CENTRAL] Arrancando la Central...")

db.ini_bd(ruta_bd)

for id_operario, nombre in operarios:
    db.alta_oper(id_operario, nombre)

state.cargar_bd()
state.desc_todas()
estaciones = state.obt_todas()
print("[CENTRAL] Estaciones registradas:", len(estaciones))
for id_estacion, datos in estaciones.items():
    print("   ", id_estacion, "-", datos["location"], "-", datos["status"])

#SERVICIOS

# Servidor de sockets
# Va en un hilo aparte porque se queda esperando conexiones para siempre.

hilo_sockets = threading.Thread(target=socket_server.ini_servidor, args=(puerto, protocol_class), daemon=True)
hilo_sockets.start()

kafka_handlers.iniciar_kafka(direccion_kafka)

# Panel web (puerto de la variable PORT, 8080 por defecto)
puerto_panel = int(os.environ.get("PORT", 8080))
threading.Thread(target=panel.ini_panel, args=(puerto_panel,), daemon=True).start()

# Menú de órdenes por consola
threading.Thread(target=commands.menu_cons, daemon=True).start()

#MANTENER LA CENTRAL ACTIVA

try:
    while True:
        time.sleep(1)

        # Si el servidor de sockets se ha caído (por ejemplo, el puerto estaba ocupado), salimos
        if not hilo_sockets.is_alive():
            print("[CENTRAL] El servidor de sockets se ha parado. Cerrando Central.")
            break

except KeyboardInterrupt:
    print("\n[CENTRAL] Central detenida.")