import socket
from common.protocol.base import BaseProtocol

# Caracteres de control ASCII (en bytes) en base al enunciado
STX = b'\x02'   # Start of TeXt (inicio del mensaje)
ETX = b'\x03'   # End of TeXt (fin del mensaje)
EOT = b'\x04'   # End Of Transmission (fin de la comunicacion)
ENQ = b'\x05'   # ENQuery (peticion de inicio de comunicacion)
ACK = b'\x06'   # ACKnowledge (confirmacion)
NACK = b'\x15'  # Negative ACKnowledge (error / mensaje rechazado)

def compute_lrc(data: bytes) -> bytes:
    """Calcula el LRC haciendo XOR de los datos + ETX"""
    lrc = 0
    for byte in data + ETX:  # Incluye ETX en el cálculo
        lrc ^= byte
    return bytes([lrc])


class StandardLRCProtocol(BaseProtocol):
    """
    Protocolo recomendado por el enunciado:
    Empaquetado: <STX><DATA><ETX><LRC>
    Flujo de sesión: 
      - Conectar: ENQ -> ACK
      - Mensajes (repetible): REQUEST (STX..ETX LRC) -> ACK -> ANSWER (STX..ETX LRC) -> ACK
      - Desconectar: EOT
    """

    def _recv_exact(self, sock: socket.socket, num_bytes: int) -> bytes:
        """Lee del socket exactamente num_bytes, acumulando en un buffer."""
        buffer = bytearray()
        while len(buffer) < num_bytes:
            chunk = sock.recv(num_bytes - len(buffer))
            if not chunk:
                raise ConnectionError("El socket se cerró antes de recibir todos los bytes esperados")
            buffer.extend(chunk)
        return bytes(buffer)

    def _pack_frame(self, message: str) -> bytes:
        """Construye la trama: <STX><DATA><ETX><LRC>"""
        data_bytes = message.encode('utf-8')
        lrc = compute_lrc(data_bytes)
        return STX + data_bytes + ETX + lrc

    def _unpack_frame(self, sock: socket.socket, allow_eot: bool = False) -> str | None:
        """
        Lee una trama <STX><DATA><ETX><LRC>, valida el LRC
        y responde automáticamente con ACK o NACK.
        Si allow_eot es True y recibe EOT, devuelve None (cierre ordenado).
        """
        first_byte = self._recv_exact(sock, 1)

        # Si el servidor está esperando petición y el cliente manda EOT para despedirse:
        if allow_eot and first_byte == EOT:
            return None

        if first_byte != STX:
            sock.sendall(NACK)
            raise ValueError(f"Trama corrupta: se esperaba STX, se recibió {first_byte}")

        # Leemos byte a byte el DATA hasta encontrar <ETX>
        payload = bytearray()
        while True:
            b = self._recv_exact(sock, 1)
            if b == ETX:
                break
            payload.extend(b)

        # El siguiente byte es <LRC>
        received_lrc = self._recv_exact(sock, 1)
        expected_lrc = compute_lrc(payload)

        # Validamos el LRC recibido con el esperado
        if received_lrc != expected_lrc:
            sock.sendall(NACK)
            raise ValueError("Error de integridad: el LRC calculado no coincide con el recibido")

        # Si todo está correcto, confirmamos con ACK
        sock.sendall(ACK)
        return payload.decode('utf-8')

    # -----------------------------
    # GESTIÓN DEL CICLO DE SESIÓN
    # -----------------------------
    def init_connection(self, sock: socket.socket) -> None:
        """Cliente: envía ENQ y espera ACK del servidor"""
        sock.sendall(ENQ)
        ack = self._recv_exact(sock, 1)
        if ack != ACK:
            raise ConnectionError(f"El servidor rechazó el ENQ inicial (recibido: {ack})")

    def accept_connection(self, sock: socket.socket) -> None:
        """Servidor: espera ENQ del cliente y responde ACK"""
        enq = self._recv_exact(sock, 1)
        if enq != ENQ:
            sock.sendall(NACK)
            raise ValueError(f"Se esperaba ENQ inicial, recibido: {enq}")
        sock.sendall(ACK)

    def close_connection(self, sock: socket.socket) -> None:
        """Cliente: avisa del cierre enviando EOT"""
        sock.sendall(EOT)

    # -----------------------------
    # INTERCAMBIO DE MENSAJES
    # -----------------------------
    def send_request(self, sock: socket.socket, message: str) -> str:
        """Cliente: envía petición empaquetada, espera ACK, y recibe la respuesta"""
        sock.sendall(self._pack_frame(message))
        ack = self._recv_exact(sock, 1)
        if ack != ACK:
            raise ConnectionError(f"El servidor rechazó la trama con NACK (recibido: {ack})")

        # Recibe respuesta del servidor (valida LRC y responde ACK)
        answer = self._unpack_frame(sock, allow_eot=False)
        return answer

    def receive_request(self, sock: socket.socket) -> str | None:
        """Servidor: recibe la petición (o None si el cliente envió EOT o cerró la conexión)"""
        try:
            return self._unpack_frame(sock, allow_eot=True)
        except ConnectionError:
            return None

    def send_response(self, sock: socket.socket, message: str) -> None:
        """Servidor: envía respuesta empaquetada y espera ACK del cliente."""
        sock.sendall(self._pack_frame(message))
        ack = self._recv_exact(sock, 1)
        if ack != ACK:
            raise ConnectionError(f"El cliente no confirmó la respuesta recibida (recibido: {ack})")