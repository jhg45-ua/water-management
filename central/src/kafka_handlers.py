import threading
import time

from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import NoBrokersAvailable

from common import messages, topics
from database import db
from src import state


OPERARIO_CENTRAL = "CENTRAL"
GRUPO = "wm-central"

productor = None


# Inicia Kafka en un hilo aparte, para que Central no se quede esperando si Kafka no está disponible.
def iniciar_kafka(servidor):
    hilo = threading.Thread(target=_arrancar, args=(servidor,), daemon=True)
    hilo.start()


# Crea el productor y los hilos que escuchan los topics (reintenta hasta que haya broker).
def _arrancar(servidor):
    global productor

    productor = _con_reintentos(lambda: KafkaProducer(bootstrap_servers=servidor), "productor")

    escuchas = [(topics.PETICIONES, manejar_peticion), (topics.TELEMETRIA, manejar_telemetria)]

    for topic, manejador in escuchas:
        hilo = threading.Thread(target=_bucle_consumidor, args=(topic, servidor, manejador), daemon=True)
        hilo.start()

    print(f"[KAFKA] Conectado a {servidor}")


# Si Kafka no está disponible, espera un poco y vuelve a intentarlo.
def _con_reintentos(crear, nombre):
    while True:
        try:
            return crear()
        except NoBrokersAvailable:
            print(f"[KAFKA] No hay broker disponible para el {nombre}. Reintentando en 3 s...")
            time.sleep(3)


# Escucha los mensajes de un topic y llama a su función correspondiente.
def _bucle_consumidor(topic, servidor, manejador):
    consumidor = _con_reintentos(lambda: KafkaConsumer(topic, bootstrap_servers=servidor, group_id=GRUPO, auto_offset_reset="latest"), f"consumidor de {topic}")

    print(f"[KAFKA] Escuchando {topic}")

    for registro in consumidor:
        mensaje = messages.de_bytes(registro.value)

        if mensaje is None:
            print(f"[KAFKA] Mensaje no válido en {topic}, se descarta")
            continue

        try:
            manejador(mensaje)
        except Exception as error:
            print(f"[KAFKA] Error al procesar un mensaje de {topic}: {error}")


# Envía un mensaje a Kafka.
def _enviar(topic, clave, mensaje):
    if productor is None:
        print("[KAFKA] Error: Kafka no está iniciado")
        return

    productor.send(topic, key=str(clave).encode("utf-8"), value=messages.a_bytes(mensaje))


# Envía una notificación al operario.
def notificar(operario, ws, evento, texto, caudal=0, volumen=0, mostrar=True):
    if mostrar:
        print(f"[RIEGO] {operario} / {ws}: {evento} - {texto}")

    mensaje = messages.msj_notif(operario, ws, evento, texto, caudal, volumen)
    _enviar(topics.NOTIF_FO, operario, mensaje)


# Envía una orden a una estación de riego.
def ordenar(ws, accion, operario=None, duracion=None):
    mensaje = messages.msj_orden(ws, accion, operario, duracion)
    _enviar(topics.ORDENES, ws, mensaje)


# Comprueba que la petición recibida sea correcta.
def manejar_peticion(mensaje):
    if mensaje["type"] != "REQUEST":
        return

    operario = mensaje.get("operator")
    ws = mensaje.get("ws")

    if not operario or not ws:
        print("[KAFKA] Petición sin operario o estación, se descarta")
        return

    procesar_peticion(operario, ws, mensaje.get("duration"))


# Comprueba si se puede realizar el riego y, si todo está bien, envía la orden para que empiece.
def procesar_peticion(operario, ws, duracion, desde_central=False):
    notificar(operario, ws, messages.EV_RECIBIDA, f"Central ha recibido la petición de riego en {ws}")

    try:
        duracion = int(duracion)
    except (TypeError, ValueError):
        duracion = 0

    if duracion <= 0:
        _denegar(operario, ws, "Duración de riego no válida")
        return False

    # Si la petición viene de un operario, comprobamos que esté registrado.
    if not desde_central and not db.hay_oper(operario):
        _denegar(operario, ws, "Operario no registrado")
        return False

    # Intentamos reservar la estación para el riego.
    reservada, motivo = state.res_riego(ws, operario)

    if not reservada:
        _denegar(operario, ws, motivo)
        return False

    notificar(operario, ws, messages.EV_AUTORIZADA, f"Riego autorizado en {ws} durante {duracion} s")
    ordenar(ws, messages.ACC_INICIAR, operario, duracion)

    return True


# Informa al operario de por qué se ha rechazado su petición.
def _denegar(operario, ws, motivo):
    notificar(operario, ws, messages.EV_DENEGADA, f"Riego denegado en {ws}: {motivo}")


# Procesa los datos que envían las estaciones de riego.
def manejar_telemetria(mensaje):
    if mensaje["type"] != "TELEMETRY":
        return

    ws = mensaje.get("ws")
    caudal = mensaje.get("flow", 0)
    volumen = mensaje.get("volume", 0)

    if not ws:
        return

    # Si el riego ha terminado, guardamos el resultado final.
    if mensaje.get("final"):
        resumen = state.fin_riego(ws, volumen)

        if resumen is not None:
            notificar(resumen["operator"], ws, messages.EV_FINAL, f"Riego terminado en {ws}: {resumen['volume']:.1f} L en {resumen['duration']} s", 0, resumen["volume"])

        return

    # Si el riego sigue activo, notificamos los datos actuales.
    if state.act_riego(ws, caudal, volumen):
        notificar(mensaje.get("operator"), ws, messages.EV_PROGRESO, f"Regando en {ws}: {caudal} L/min, {volumen} L", caudal, volumen, mostrar=False)


# Detiene el riego cuando se detecta una fuga.
def estacion_con_fuga(ws):
    resumen = state.fij_estado(ws, state.LEAK)

    if resumen is not None:
        ordenar(ws, messages.ACC_PARAR)
        notificar(resumen["operator"], ws, messages.EV_FUGA, f"Riego cortado en {ws} por una fuga: {resumen['volume']:.1f} L en {resumen['duration']} s", 0, resumen["volume"])


# Actúa cuando una estación se desconecta durante el riego.
def estacion_desconectada(ws):
    resumen = state.fij_estado(ws, state.DISCONNECTED)

    if resumen is not None:
        ordenar(ws, messages.ACC_PARAR)
        notificar(resumen["operator"], ws, messages.EV_FINAL, f"Riego interrumpido en {ws}: la estación se ha desconectado ({resumen['volume']:.1f} L en {resumen['duration']} s)", 0, resumen["volume"])


# Permite iniciar un riego desde la propia Central.
def iniciar_riego_central(ws, duracion):
    return procesar_peticion(OPERARIO_CENTRAL, ws, duracion, desde_central=True)


# Bloquea una estación para que no pueda seguir regando.
def bloquear_estacion(ws):
    bloqueada, resumen = state.cambiar_si(ws, (state.ACTIVE, state.WATERING), state.OUT_OF_SERVICE)

    if not bloqueada:
        return False

    ordenar(ws, messages.ACC_BLOQUEAR)

    if resumen is not None:
        notificar(resumen["operator"], ws, messages.EV_FINAL, f"Riego cortado en {ws}: la estación ha sido bloqueada por Central ({resumen['volume']:.1f} L en {resumen['duration']} s)", 0, resumen["volume"])

    return True


# Vuelve a activar una estación que estaba fuera de servicio.
def activar_estacion(ws):
    activada, _ = state.cambiar_si(ws, (state.OUT_OF_SERVICE,), state.ACTIVE)

    if activada:
        ordenar(ws, messages.ACC_ACTIVAR)

    return activada