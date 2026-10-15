# WM_Central.py
# Programa principal de la Central de WaterManagement.
# Es lo primero que se ejecuta: prepara la base de datos, carga las estaciones
# y pone en marcha los servicios (de momento, el servidor de sockets).
#
# Uso:      python WM_Central.py <puerto> [ip_kafka:puerto_kafka] [ruta_bd]
# Ejemplo:  python WM_Central.py 5000 localhost:9092

import os
import sys
import threading
import time

# La carpeta "common" está fuera de "central", así que añadimos la carpeta
# de arriba a la ruta de Python para poder importarla.
carpeta_raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(carpeta_raiz)

from database import db
from src import state
from src import socket_server

# Operarios que se dan de alta al arrancar. Si hace falta alguno más, se añade aquí.
operarios = [
    ("OP01", "Operario 1"),
    ("OP02", "Operario 2"),
    ("OP03", "Operario 3"),
]


# ---------------------------------------------------------------
# 1. LEER LOS PARÁMETROS
# ---------------------------------------------------------------

if len(sys.argv) < 2:
    print("Uso: python WM_Central.py <puerto> [ip_kafka:puerto_kafka] [ruta_bd]")
    sys.exit(1)

try:
    puerto = int(sys.argv[1])
except ValueError:
    print("El puerto tiene que ser un número")
    sys.exit(1)

# Estos dos son opcionales: si no se indican, se usan valores por defecto
direccion_kafka = "localhost:9092"
if len(sys.argv) > 2:
    direccion_kafka = sys.argv[2]

ruta_bd = None
if len(sys.argv) > 3:
    ruta_bd = sys.argv[3]


# ---------------------------------------------------------------
# 2. PREPARAR LA BASE DE DATOS Y EL ESTADO
# ---------------------------------------------------------------

print("[CENTRAL] Arrancando la Central...")

# Creamos las tablas si no existen
db.ini_bd(ruta_bd)

# Damos de alta a los operarios (si ya existían, no pasa nada)
for id_operario, nombre in operarios:
    db.alta_oper(id_operario, nombre)

# Cargamos las estaciones guardadas en la BD y las ponemos todas desconectadas,
# porque hasta que no conecten no sabemos cómo están
state.cargar_bd()
state.desc_todas()

estaciones = state.obt_todas()
print("[CENTRAL] Estaciones registradas:", len(estaciones))
for id_estacion, datos in estaciones.items():
    print("   ", id_estacion, "-", datos["location"], "-", datos["status"])


# ---------------------------------------------------------------
# 3. PONER EN MARCHA LOS SERVICIOS
# ---------------------------------------------------------------

# Servidor de sockets (los Monitores se conectan aquí).
# Va en un hilo aparte porque se queda esperando conexiones para siempre.
hilo_sockets = threading.Thread(target=socket_server.ini_servidor, args=(puerto,), daemon=True)
hilo_sockets.start()

# PENDIENTE: aquí se arrancará el hilo de Kafka (direccion_kafka) y el del panel.

print("[CENTRAL] Central en marcha. Pulsa Ctrl+C para pararla.")


# ---------------------------------------------------------------
# 4. MANTENER LA CENTRAL VIVA
# ---------------------------------------------------------------

# Los hilos son "daemon", así que si el programa principal termina, se acaban con él.
# Por eso el programa principal se queda aquí esperando.
try:
    while True:
        time.sleep(1)

        # Si el servidor de sockets se ha caído (por ejemplo, el puerto estaba ocupado), salimos
        if not hilo_sockets.is_alive():
            print("[CENTRAL] El servidor de sockets se ha parado. Cerrando Central.")
            break

except KeyboardInterrupt:
    print("\n[CENTRAL] Central detenida.")