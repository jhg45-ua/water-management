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
                raise ConnectionError("El socket se cerró inesperadamente mientras se leía")
            if chunk == DELIMITER:
                break
            buffer.extend(chunk)
        return buffer.decode('utf-8')

    # Lado Cliente
    def send_request(self, sock: socket.socket, message: str) -> str:
        """Envía el mensaje directamente con \n y espera la respuesta"""
        # Enviar petición con delimitador
        payload = (message + '\n').encode('utf-8')
        sock.sendall(payload)
        # Recibir respuesta
        answer = self._recv_line(sock)
        return answer
    
    # Lado Servidor
    def receive_request(self, sock: socket.socket) -> str:
        """Espera y lee la petición directamente"""
        return self._recv_line(sock)
    
    def send_response(self, sock: socket.socket, message: str) -> None:
        """Envía la respuesta con delimitador"""
        payload = (message + '\n').encode('utf-8')
        sock.sendall(payload)