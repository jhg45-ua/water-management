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
    """Calcula el Longitudinal Redundancy Check haciendo XOR de cada byte"""
    lrc = 0
    for byte in data:
        lrc ^= byte # Operador XOR
    return bytes([lrc])


class StandardLRCProtocol(BaseProtocol):
    """
    Protocolo recomendado por el enunciado:
    Empaquetado: <STX><DATA><ETX><LRC>
    Flujo: ENQ -> ACK -> REQUEST -> ACK -> ANSWER -> ACK -> EOT
    """

    def _recv_exect(self, sock: socket.socket, num_bytes: int) -> bytes:
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

    def _unpack_frame(self, sock: socket.socket) -> str:
        """
        Lee una trama <STX><DATA><ETX><LRC>, valida el LRC
        y responde automáticamente con ACK o NACK.
        """
        # Esperamos obligatoriamente que empiece por <STX>
        stx = self._recv_exect(sock, 1)
        if stx != STX:
            raise ValueError(f"Trama corrupta: se esperaba STX, se recibió {stx}")

        # Leemos byte a byte el DATA hasta encontrar <ETX>
        payload = bytearray()
        while True:
            b = self._recv_exect(sock, 1)
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