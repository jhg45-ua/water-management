# protocol.py
# Aquí está el protocolo de sockets que usan todos los módulos (Central, Monitor y Engine).
# Sigue el flujo recomendado en el enunciado:
#
#   Cliente                          Servidor
#   -------                          --------
#   ENQ                 ------->
#                       <-------     ACK / NACK
#   STX REQUEST ETX LRC ------->
#                       <-------     ACK / NACK
#                       <-------     STX ANSWER ETX LRC
#   ACK / NACK          ------->
#   EOT                 ------->     (y se cierra la conexión)
#
# El LRC es un XOR byte a byte del mensaje. Sirve para que el que recibe
# compruebe que el mensaje no ha llegado corrupto.

import random
import time

# Caracteres de control (son bytes sueltos)
STX = b"\x02"   # inicio del mensaje
ETX = b"\x03"   # fin del mensaje
EOT = b"\x04"   # fin de la comunicación
ENQ = b"\x05"   # el cliente pide empezar a hablar
ACK = b"\x06"   # recibido correctamente
NACK = b"\x15"  # recibido con error

# Los campos de un mensaje van separados por este carácter.
# Ejemplo: "AUTH#WS01#Jardin norte" -> operación AUTH, campos WS01 y Jardin norte
SEPARATOR = "#"


def calc_lrc(datos):
    """Calcula el LRC: el XOR de todos los bytes.
    Incluimos el ETX en el cálculo (así lo hace el estándar STX/ETX/LRC).
    Quien envía y quien recibe tienen que calcularlo igual, por eso está aquí."""
    lrc = 0

    for byte in datos + ETX:
        lrc = lrc ^ byte

    return lrc


def armar_msj(texto):
    """Convierte un texto en el paquete que se envía por el socket:
    STX + texto + ETX + LRC."""
    datos = texto.encode()

    return STX + datos + ETX + bytes([calc_lrc(datos)])


def leer_n(socket, cantidad):
    """Lee exactamente 'cantidad' bytes del socket.
    Si el otro lado cierra la conexión, lanza ConnectionError."""
    resultado = b""

    while len(resultado) < cantidad:
        fragmento = socket.recv(cantidad - len(resultado))

        if fragmento == b"":
            raise ConnectionError("Conexión cerrada por el otro extremo")

        resultado += fragmento

    return resultado


def recib(socket):
    """Lee lo siguiente que llegue por el socket y dice de qué tipo es.
    Devuelve una pareja (tipo, contenido):
      ("CONTROL", byte)  -> ha llegado ENQ, EOT, ACK o NACK
      ("MESSAGE", texto) -> ha llegado un mensaje completo y correcto
      ("BAD", None)      -> ha llegado algo mal formado o con el LRC incorrecto
    Si se cierra la conexión, lanza ConnectionError."""
    primero = leer_n(socket, 1)

    # Si es un carácter de control, ya está
    if primero in (ENQ, EOT, ACK, NACK):
        return ("CONTROL", primero)

    # Si no empieza por STX, no es un mensaje válido
    if primero != STX:
        return ("BAD", None)

    # Leemos byte a byte hasta encontrar el ETX
    datos = b""

    while True:
        byte = leer_n(socket, 1)

        if byte == ETX:
            break

        datos += byte

    # Después del ETX viene el LRC, que es un solo byte
    lrc_recibido = leer_n(socket, 1)[0]

    if lrc_recibido != calc_lrc(datos):
        return ("BAD", None)

    return ("MESSAGE", datos.decode())


# ---------------------------------------------------------------
# FUNCIONES PARA EL LADO CLIENTE (el que empieza la conversación)
# ---------------------------------------------------------------

def ini_conex(socket):
    """Envía el ENQ y espera el ACK del servidor.
    Devuelve True si el servidor ha aceptado."""
    socket.sendall(ENQ)

    tipo, contenido = recib(socket)

    return tipo == "CONTROL" and contenido == ACK


def env_pet(socket, texto):
    """Envía una petición y devuelve el texto de la respuesta del servidor.
    Si algo falla (NACK, mensaje corrupto...) devuelve None."""
    socket.sendall(armar_msj(texto))

    # Primero el servidor confirma que ha recibido bien la petición
    tipo, contenido = recib(socket)

    if tipo != "CONTROL" or contenido != ACK:
        return None

    # Después llega la respuesta, y la confirmamos con ACK o NACK
    tipo, respuesta = recib(socket)

    if tipo == "MESSAGE":
        socket.sendall(ACK)
        return respuesta

    socket.sendall(NACK)
    return None


def env_pet_reint(socket, texto, intentos=3):
    """Como env_pet, pero si falla reintenta esperando el doble cada vez
    (1 s, 2 s, 4 s...) más un poco de azar (jitter) para no saturar.
    Solo para peticiones idempotentes: repetirlas no debe causar problemas."""
    espera = 1

    for intento in range(intentos):
        respuesta = env_pet(socket, texto)

        if respuesta is not None:
            return respuesta

        if intento < intentos - 1:
            time.sleep(espera + random.random())
            espera = espera * 2

    return None


def fin_conex(socket):
    """Avisa al servidor de que hemos terminado."""
    socket.sendall(EOT)


# ---------------------------------------------------------------
# FUNCIONES PARA EL LADO SERVIDOR
# ---------------------------------------------------------------

def env_resp(socket, texto):
    """Envía una respuesta y espera el ACK del cliente.
    Devuelve True si el cliente la ha recibido bien."""
    socket.sendall(armar_msj(texto))

    tipo, contenido = recib(socket)

    return tipo == "CONTROL" and contenido == ACK