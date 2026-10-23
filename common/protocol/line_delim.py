import socket
from common.protocol.base import BaseProtocol

DELIMITER = b'\n'

class LineDelimitedProtocol(BaseProtocol):
    """
    Protocolo moderno basado en mensajes delimitados por salto de línea (\n).
    - Sin handshakes innecesarios (sin ENQ/ACK/EOT).
    - Confiamos en la integridad y orden garantizados por TCP.
    - Flujo directo: REQUEST -> ANSWER.
    """

    def _recv_line(self, sock: socket.socket) -> str:
        """Lee del socket byte a byte hasta encontrar el salto de línea"""
        buffer = bytearray()
        while True:
            chunk = sock.recv(1)
            if not chunk:
                raise ConnectionError("El socket se cerró mientras se leía")
            if chunk == DELIMITER:
                break
            buffer.extend(chunk)
        return buffer.decode('utf-8')

    # Lado Cliente
    def send_request(self, sock: socket.socket, message: str) -> str:
        """Envía el mensaje con \n y espera la respuesta"""
        payload = (message + '\n').encode('utf-8')
        sock.sendall(payload)
        return self._recv_line(sock)
    
    # Lado Servidor
    def receive_request(self, sock: socket.socket) -> str | None:
        """Espera y lee la petición directamente. Si el socket se cierra, retorna None"""
        try:
            return self._recv_line(sock)
        except ConnectionError:
            return None
    
    def send_response(self, sock: socket.socket, message: str) -> None:
        """Envía la respuesta con delimitador \n"""
        payload = (message + '\n').encode('utf-8')
        sock.sendall(payload)