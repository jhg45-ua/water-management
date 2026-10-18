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

servidor_kafka = f"{dir_kafka}:{puerto_kafka}"

def escuchar_kafka():
    global productor, estaciones_actuales

    # Reintentos de conexión por si Kafka está arrancando
    while True:
        try:
            productor = KafkaProducer(bootstrap_servers=servidor_kafka)
            consumidor = KafkaConsumer(
                topics.NOTIF_FO,
                topics.ESTACIONES,
                bootstrap_servers=servidor_kafka,
                group_id=f"fo-{id_operador}-{int(time.time())}", # Group ID único por operario
                auto_offset_reset="latest"
            )
            print(f"[{id_operador}] Conectado a Kafka ({servidor_kafka}).")
            break
        except Exception:
            time.sleep(2)

    for msg in consumidor:
        datos = messages.de_bytes(msg.value)
        if not datos:
            continue

        tipo = datos.get("type")

        # Catálogo de estaciones emitido por Central cada 1 segundo
        if tipo == "STATIONS":
            estaciones_actuales = datos.get("stations", {})

        # Notificaciones de riego
        elif tipo == "NOTIFY":
            if datos.get("operator") == id_operador:
                evento = datos.get("event")
                texto = datos.get("text", "")
                ws = datos.get("ws", "")

                if evento == messages.EV_RECIBIDA:
                    print(f"\n[{id_operador}] {texto}")
                elif evento == messages.EV_AUTORIZADA:
                    print(f"\n[{id_operador}] {texto}")
                elif evento == messages.EV_DENEGADA:
                    print(f"\n[{id_operador}] {texto}")
                    evento_fin_riego.set() # Concluido (denegado)
                elif evento == messages.EV_PROGRESO:
                    caudal = datos.get("flow", 0)
                    volumen = datos.get("volume", 0)
                    print(f"[{id_operador} - {ws}] {caudal} L/min | Acumulado: {volumen} L")
                elif evento in (messages.EV_FINAL, messages.EV_FUGA):
                    print(f"\n[{id_operador}] 🏁 {texto}")
                    evento_fin_riego.set() # Concluido (éxito o corte)

def pedir_riego(ws, duracion):
    # Aseguramos que el productor esté listo
    while productor is None:
        time.sleep(0.5)

    evento_fin_riego.clear()
    pet = messages.msj_pet(id_operador, ws, duracion)
    productor.send(topics.PETICIONES, messages.a_bytes(pet))
    productor.flush()
    print(f"[{id_operador}] Petición enviada: {ws} durante {duracion} s. Esperando resultado...")
    
    # Bloquea hasta que Central avise de que el servicio ha finalizado (sea DENIED, FINISHED o LEAK_STOP)
    evento_fin_riego.wait()

def modo_fichero(ruta):
    if not os.path.exists(ruta):
        print(f"[{id_operador}] Error: El fichero '{ruta}' no existe.")
        return

    print(f"[{id_operador}] Procesando fichero de servicios: '{ruta}'")
    with open(ruta, "r") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#"):
                continue

            partes = linea.split()
            if len(partes) < 2:
                continue

            ws = partes[0]
            try:
                duracion = int(partes[1])
            except ValueError:
                continue

            pedir_riego(ws, duracion)

            # Espera obligatoria del enunciado (4 segundos entre servicios)
            print(f"[{id_operador}] Esperando 4 segundos antes de la siguiente petición...")
            time.sleep(4)

    print(f"[{id_operador}] Todos los servicios del fichero han sido procesados.")

def modo_manual():
    while True:
        print(f"\n--- MENÚ OPERARIO: {id_operador} ---")
        print("1) Ver estaciones disponibles")
        print("2) Solicitar riego")
        print("0) Salir")
        opcion = input("> ").strip()

        if opcion == "1":
            print(f"\nEstaciones registradas ({len(estaciones_actuales)}):")
            for ws, d in estaciones_actuales.items():
                estado = d.get("status", "UNKNOWN")
                loc = d.get("location", "")
                simbolo = "ACTIVE" if estado == "ACTIVE" else ("WATERING" if estado == "WATERING" else "RED")
                print(f"   {simbolo} {ws} ({loc}) -> {estado}")

        elif opcion == "2":
            ws = input("ID de la estación (ej. WS-01): ").strip()
            try:
                duracion = int(input("Duración en segundos: ").strip())
                pedir_riego(ws, duracion)
            except ValueError:
                print("La duración debe ser un número entero.")

        elif opcion == "0":
            break

# Arrancamos el hilo de Kafka en segundo plano
threading.Thread(target=escuchar_kafka, daemon=True).start()

# Esperamos un segundo para conectar antes de mostrar el menú
time.sleep(1)

try:
    if fichero_servicios:
        modo_fichero(fichero_servicios)
    else:
        modo_manual()
except KeyboardInterrupt:
    print(f"\n[{id_operador}] Saliendo...")