import os
import sys
import time
import threading
from kafka import KafkaConsumer, KafkaProducer

# Añadimos la raíz del proyecto al path de Python para importar common
carpeta_raiz = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(carpeta_raiz)

from common import topics, messages

if len(sys.argv) < 3:
    print("Uso:python WM_FO.py <ip_kafka:puerto_kafka> <id_operador> [fichero_servicios]")
    sys.exit(1)
try:
    # Estos dos son obligatorios: la dirección del servidor Kafka y el ID del operador
    dir_kafka, puerto_kafka = sys.argv[1].split(":")
    puerto_kafka = int(puerto_kafka)
    id_operador = sys.argv[2]
except ValueError:
    print("El puerto tiene que ser un número")
    sys.exit(1)

if len(sys.argv) > 3:
    fichero_servicios = sys.argv[3]
else:
    fichero_servicios = None

productor = None
estaciones_actuales = {}
evento_fin_riego = threading.Event()