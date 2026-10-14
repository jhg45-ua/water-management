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


def calcular_lrc(datos):
    """Calcula el LRC: el XOR de todos los bytes.
    Incluimos el ETX en el cálculo (así lo hace el estándar STX/ETX/LRC).
    Quien envía y quien recibe tienen que calcularlo igual, por eso está aquí."""
    lrc = 0

    for byte in datos + ETX:
        lrc = lrc ^ byte

    return lrc


def construir_mensaje(texto):
    """Convierte un texto en el paquete que se envía por el socket:
    STX + texto + ETX + LRC."""
    datos = texto.encode()

    return STX + datos + ETX + bytes([calcular_lrc(datos)])


def leer_bytes_exactos(socket, cantidad):
    """Lee exactamente 'cantidad' bytes del socket.
    Si el otro lado cierra la conexión, lanza ConnectionError."""
    resultado = b""

    while len(resultado) < cantidad:
        fragmento = socket.recv(cantidad - len(resultado))

        if fragmento == b"":
            raise ConnectionError("Conexión cerrada por el otro extremo")

        resultado += fragmento

    return resultado


def recibir(socket):
    """Lee lo siguiente que llegue por el socket y dice de qué tipo es.
    Devuelve una pareja (tipo, contenido):
      ("CONTROL", byte)  -> ha llegado ENQ, EOT, ACK o NACK
      ("MESSAGE", texto) -> ha llegado un mensaje completo y correcto
      ("BAD", None)      -> ha llegado algo mal formado o con el LRC incorrecto
    Si se cierra la conexión, lanza ConnectionError."""
    primero = leer_bytes_exactos(socket, 1)

    # Si es un carácter de control, ya está
    if primero in (ENQ, EOT, ACK, NACK):
        return ("CONTROL", primero)

    # Si no empieza por STX, no es un mensaje válido
    if primero != STX:
        return ("BAD", None)

    # Leemos byte a byte hasta encontrar el ETX
    datos = b""

    while True:
        byte = leer_bytes_exactos(socket, 1)

        if byte == ETX:
            break

        datos += byte

    # Después del ETX viene el LRC, que es un solo byte
    lrc_recibido = leer_bytes_exactos(socket, 1)[0]

    if lrc_recibido != calcular_lrc(datos):
        return ("BAD", None)

    return ("MESSAGE", datos.decode())


# ---------------------------------------------------------------
# FUNCIONES PARA EL LADO CLIENTE (el que empieza la conversación)
# ---------------------------------------------------------------

def iniciar_conexion(socket):
    """Envía el ENQ y espera el ACK del servidor.
    Devuelve True si el servidor ha aceptado."""
    socket.sendall(ENQ)

    tipo, contenido = recibir(socket)

    return tipo == "CONTROL" and contenido == ACK


def enviar_peticion(socket, texto):
    """Envía una petición y devuelve el texto de la respuesta del servidor.
    Si algo falla (NACK, mensaje corrupto...) devuelve None."""
    socket.sendall(construir_mensaje(texto))

    # Primero el servidor confirma que ha recibido bien la petición
    tipo, contenido = recibir(socket)

    if tipo != "CONTROL" or contenido != ACK:
        return None

    # Después llega la respuesta, y la confirmamos con ACK o NACK
    tipo, respuesta = recibir(socket)

    if tipo == "MESSAGE":
        socket.sendall(ACK)
        return respuesta

    socket.sendall(NACK)
    return None


def finalizar_conexion(socket):
    """Avisa al servidor de que hemos terminado."""
    socket.sendall(EOT)


# ---------------------------------------------------------------
# FUNCIONES PARA EL LADO SERVIDOR
# ---------------------------------------------------------------

def enviar_respuesta(socket, texto):
    """Envía una respuesta y espera el ACK del cliente.
    Devuelve True si el cliente la ha recibido bien."""
    socket.sendall(construir_mensaje(texto))

    tipo, contenido = recibir(socket)

    return tipo == "CONTROL" and contenido == ACK
