from abc import ABC, abstractmethod
import socket

# Interfaz base para los protocolos de comunicación por sockets
# Por eso usamos @abstractmethod y no implementamos nada aquí, solo definimos la interfaz.
class BaseProtocol(ABC):
    """Interfaz base para los protocolos de comunicacion por sockets"""

    @abstractmethod
    def send_request(self, sock: socket.socket, message: str) -> str:
        """Cliente: envia peticion y recibe respuesta del servidor"""
        pass

    @abstractmethod
    def receive_request(self, sock: socket.socket) -> str:
        "Servidor: recibe peticion del cliente"
        pass

    @abstractmethod
    def send_response(self, sock: socket.socket, message: str) -> str:
        """Servidor: envia la respuesta al cliente"""
        pass