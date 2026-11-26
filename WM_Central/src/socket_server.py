import socket
import threading
import time
import os

from common.protocol.standard_lrc import StandardLRCProtocol
from common.protocol.line_delim import LineDelimitedProtocol
from src import state
from src import kafka_handlers
from database import db

SEPARATOR = "#"

PROTOCOLS = {
    "lrc": StandardLRCProtocol,
    "line": LineDelimitedProtocol
}

MAX_MON = 50
TIEMPO_ESPERA = 5
TIEMPO_VIDA = int(os.environ.get("TIEMPO_VIDA", 15))  # segundos sin noticias del Monitor = caído (0 = desactivado)
ESPERA_VIDA = TIEMPO_VIDA or None
cupo = threading.BoundedSemaphore(MAX_MON)


def reg(texto):
    print(time.strftime("%H:%M:%S"), texto)


def ini_servidor(puerto, protocol_class=StandardLRCProtocol):
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        servidor.bind(("0.0.0.0", puerto))
    except OSError:
        reg(f"[SOCKETS] No se puede abrir el puerto {puerto} (¿ya está en uso?)")
        return

    servidor.listen()
    reg(f"[SOCKETS] Escuchando Monitores en el puerto {puerto}")

    while True:
        conexion, direccion = servidor.accept()
        ip_cliente = direccion[0]

        if not cupo.acquire(blocking=False):
            reg(f"[SOCKETS] Demasiadas conexiones, se rechaza {direccion}")
            db.reg_auditoria(
                "WM_WS_M", "UNKNOWN", ip_cliente, "CONNECTION_REJECTED", "WARNING",
                f"Conexión rechazada: límite máximo alcanzado ({MAX_MON})",
                {"max_mon": MAX_MON},
            )
            conexion.close()
            continue

        reg(f"[SOCKETS] Nueva conexión desde {direccion}")

        threading.Thread(
            target=atender_mon,
            args=(conexion, protocol_class, ip_cliente),
            daemon=True,
        ).start()


def atender_mon(conexion, protocol_class=StandardLRCProtocol, ip_cliente="unknown"):
    id_estacion = None
    protocol = protocol_class()

    try:
        conexion.settimeout(ESPERA_VIDA)
        protocol.accept_connection(conexion)

        while True:
            peticion = protocol.receive_request(conexion)

            if peticion is None:
                break

            conexion.settimeout(TIEMPO_ESPERA)
            respuesta, id_estacion = proc_pet(peticion, id_estacion, ip_cliente)
            protocol.send_response(conexion, respuesta)
            conexion.settimeout(ESPERA_VIDA)

    except (ConnectionError, OSError, ValueError) as err:
        db.reg_auditoria(
            "WM_WS_M", id_estacion or "UNKNOWN", ip_cliente, "SOCKET_ERROR", "WARNING",
            f"Error o timeout en conexión de {id_estacion or 'cliente'}: {err}",
            {"ws_id": id_estacion, "error": str(err)},
        )

    finally:
        if id_estacion is not None:
            kafka_handlers.estacion_desconectada(id_estacion)
            db.reg_auditoria(
                "WM_WS_M", id_estacion, ip_cliente, "WS_DISCONNECTED", "WARNING",
                f"{id_estacion} desconectada",
                {"ws_id": id_estacion},
            )
            reg(f"[SOCKETS] {id_estacion} desconectada")

        conexion.close()
        cupo.release()


def proc_pet(texto, id_estacion, ip_cliente="unknown"):
    partes = texto.split(SEPARATOR)
    operacion = partes[0]

    # PING : mensaje de vida del Monitor (que llegue ya basta para saber que sigue vivo)
    if operacion == "PING":
        return "OK", id_estacion

    # REGISTER#id#ubicacion : da de alta una estación nueva (o actualiza su ubicación)
    if operacion == "REGISTER":
        if len(partes) < 3 or partes[1] == "":
            db.reg_auditoria(
                "WM_WS_M", "UNKNOWN", ip_cliente, "REGISTER_FAIL", "WARNING",
                "Mensaje REGISTER con formato incorrecto",
                {"raw": texto},
            )
            return "KO#Mensaje REGISTER incorrecto", id_estacion

        state.alta_estac(partes[1], partes[2])
        state.fij_ip(partes[1], ip_cliente)
        db.reg_auditoria(
            "WM_WS_M", partes[1], ip_cliente, "REGISTER", "INFO",
            f"{partes[1]} registrada en {partes[2]}",
            {"ws_id": partes[1], "location": partes[2]},
        )
        reg(f"[SOCKETS] {partes[1]} registrada en {partes[2]}")
        return "OK", id_estacion

    # AUTH#id (estricta: la estación debe estar registrada) o AUTH#id#ubicacion (la registra si hace falta)
    if operacion == "AUTH":
        if len(partes) < 2 or partes[1] == "":
            db.reg_auditoria(
                "WM_WS_M", "UNKNOWN", ip_cliente, "AUTH_FAIL", "SECURITY",
                "Mensaje AUTH con formato incorrecto",
                {"raw": texto},
            )
            return "KO#Mensaje AUTH incorrecto", id_estacion

        nuevo_id = partes[1]

        # AUTH repetido en la misma conexión (p. ej. un reintento)
        if nuevo_id == id_estacion:
            return "OK", id_estacion

        if len(partes) >= 3:
            state.alta_estac(nuevo_id, partes[2])
        elif not state.hay_estac(nuevo_id):
            db.reg_auditoria(
                "WM_WS_M", nuevo_id, ip_cliente, "AUTH_FAIL", "SECURITY",
                f"Autenticación rechazada para {nuevo_id}: WS no registrada",
                {"ws_id": nuevo_id, "reason": "not_registered"},
            )
            return "KO#WS no registrada", id_estacion

        # Transición atómica de DISCONNECTED a ACTIVE para evitar condiciones de carrera
        ok, _ = state.cambiar_si(nuevo_id, (state.DISCONNECTED,), state.ACTIVE)
        if not ok:
            db.reg_auditoria(
                "WM_WS_M", nuevo_id, ip_cliente, "AUTH_FAIL", "SECURITY",
                f"Autenticación rechazada para {nuevo_id}: estación ya conectada",
                {"ws_id": nuevo_id, "reason": "already_connected"},
            )
            return "KO#Estación ya conectada", id_estacion

        state.fij_ip(nuevo_id, ip_cliente)
        db.reg_auditoria(
            "WM_WS_M", nuevo_id, ip_cliente, "AUTH_OK", "SECURITY",
            f"{nuevo_id} autenticada correctamente",
            {"ws_id": nuevo_id},
        )
        reg(f"[SOCKETS] {nuevo_id} autenticada")
        return "OK", nuevo_id

    if id_estacion is None:
        db.reg_auditoria(
            "WM_WS_M", "UNKNOWN", ip_cliente, "UNAUTHENTICATED_CMD", "SECURITY",
            f"Operación '{operacion}' rechazada: cliente no autenticado",
            {"operation": operacion},
        )
        return "KO#No autenticado", id_estacion

    # LEAK#id y RECOVERED#id
    if operacion in ("LEAK", "RECOVERED"):
        if len(partes) < 2 or partes[1] != id_estacion:
            db.reg_auditoria(
                "WM_WS_M", id_estacion, ip_cliente, "PROTOCOL_ERROR", "WARNING",
                f"ID incorrecto en {operacion}: recibido {partes[1] if len(partes) > 1 else None}",
                {"operation": operacion, "received_id": partes[1] if len(partes) > 1 else None},
            )
            return "KO#Id incorrecto", id_estacion

        if operacion == "LEAK":
            kafka_handlers.estacion_con_fuga(id_estacion)
            db.reg_auditoria(
                "WM_WS_M", id_estacion, ip_cliente, "LEAK", "ERROR",
                f"Avería en {id_estacion}: fuga detectada",
                {"ws_id": id_estacion},
            )
            reg(f"[SOCKETS] AVERÍA en {id_estacion}: fuga detectada")
        else:
            state.cambiar_si(id_estacion, (state.LEAK,), state.ACTIVE)
            db.reg_auditoria(
                "WM_WS_M", id_estacion, ip_cliente, "RECOVERED", "INFO",
                f"{id_estacion} recuperada de fuga y vuelve a ACTIVE",
                {"ws_id": id_estacion},
            )
            reg(f"[SOCKETS] {id_estacion} recuperada")

        return "OK", id_estacion

    db.reg_auditoria(
        "WM_WS_M", id_estacion, ip_cliente, "UNKNOWN_OPERATION", "WARNING",
        f"Operación desconocida '{operacion}' desde {id_estacion}",
        {"operation": operacion},
    )
    return "KO#Operación desconocida", id_estacion