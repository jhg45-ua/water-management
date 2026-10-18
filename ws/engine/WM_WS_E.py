import os
import sys
import socket
import time
import threading

carpeta_raiz = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(carpeta_raiz)

from common.protocol.standard_lrc import StandardLRCProtocol
from common.protocol.line_delim import LineDelimitedProtocol

import random
from kafka import KafkaConsumer, KafkaProducer
from common import topics, messages

regando = False
productor_kafka = None

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
    print(f"[{id_ws}] Pulsa 'k' + Enter para simular avería, 'r' + Enter para recuperar.")
    while True:
        try:
            linea = input()
            if "k" in linea.lower():
                averia = True
                print(f"[{id_ws}] Avería simulada activada (respondiendo KO)")
            elif "r" in linea.lower():
                averia = False
                print(f"[{id_ws}] Avería reparada (respondiendo OK)")
            elif "s" in linea.lower():
                if regando:
                    print(f"[{id_ws}] Parada manual de riego solicitada.")
                    regando = False
        except EOFError:
            break

def simular_riego(operario, duracion):
    global regando
    regando = True
    volumen_total = 0.0

    print(f"[{id_ws}] Electroválvula ABIERTA. Regando ({duracion} s) para operario {operario}...")

    for segundo in range(1, duracion + 1):
        # Si se cancela por STOP o si salta una avería/fuga ('k'), cortamos de inmediato
        if not regando or averia:
            print(f"[{id_ws}] Riego detenido inmediatamente.")
            break

        time.sleep(1)

        # Simulamos un caudal realista (entre 10.0 y 14.0 L/min)
        caudal = round(random.uniform(10.0, 14.0), 1)
        # Cada segundo aporta caudal / 60 litros
        volumen_total += round(caudal / 60.0, 2)

        # Emitir telemetría periódica a Central (final=False)
        telem = messages.msj_telem(id_ws, operario, caudal, round(volumen_total, 2), final=False)
        productor_kafka.send(topics.TELEMETRIA, messages.a_bytes(telem))
        print(f"[{id_ws}] Telemetría ({segundo}/{duracion} s): {caudal} L/min | Total: {round(volumen_total, 2)} L")

    regando = False
    # Solo enviamos fin normal si NO ha sido provocado por una fuga ('k')
    if not averia:
        telem_final = messages.msj_telem(id_ws, operario, 0, round(volumen_total, 2), final=True)
        productor_kafka.send(topics.TELEMETRIA, messages.a_bytes(telem_final))
        productor_kafka.flush()
        print(f"[{id_ws}] Electroválvula CERRADA. Riego finalizado. Consumo total: {round(volumen_total, 2)} L")
    else:
        print(f"[{id_ws}] Electroválvula CERRADA por FUGA. Riego abortado.")

def escuchar_kafka():
    global productor_kafka, regando
    servidor_kafka = f"{dir_kafka}:{puerto_kafka}"

    # Reintenta conectar hasta que Kafka esté listo
    while True:
        try:
            # 1. Crear el productor de telemetría
            productor_kafka = KafkaProducer(bootstrap_servers=servidor_kafka)

            # 2. Crear el consumidor de órdenes
            consumidor = KafkaConsumer(
                topics.ORDENES,
                bootstrap_servers=servidor_kafka,
                group_id=f"engine-{id_ws}",
                auto_offset_reset="latest"
            )
            print(f"[{id_ws}] Conectado a Kafka ({servidor_kafka}). Escuchando órdenes...")
            break
        except Exception:
            time.sleep(2)

    # 3. Procesar las órdenes que van llegando
    for msg in consumidor:
        orden = messages.de_bytes(msg.value)
        if not orden or orden.get("type") != "COMMAND":
            continue

        destino = orden.get("ws")
        # Procesamos si la orden es para nosotros o para TODAS las estaciones ("ALL")
        if destino == id_ws or destino == messages.TODAS:
            accion = orden.get("action")

            if accion == messages.ACC_INICIAR:
                if averia:
                    print(f"[{id_ws}] Rechazando orden de riego: estación en AVERÍA")
                elif regando:
                    print(f"[{id_ws}] Ya hay un riego en curso")
                else:
                    duracion = orden.get("duration", 30)
                    operario = orden.get("operator", "DESCONOCIDO")
                    threading.Thread(target=simular_riego, args=(operario, duracion), daemon=True).start()

            elif accion in (messages.ACC_PARAR, messages.ACC_BLOQUEAR):
                if regando:
                    print(f"[{id_ws}] Orden de parada recibida de Central.")
                    regando = False

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
                # Hilo del teclado
                threading.Thread(target=leer_teclado, daemon=True).start()
                
                # Hilo de Kafka (ahora que ya sabemos nuestro id_ws)
                threading.Thread(target=escuchar_kafka, daemon=True).start()

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