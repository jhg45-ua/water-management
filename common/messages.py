import json

TODAS = "ALL"  # valor de "ws" para dirigirse a todas las estaciones

# Eventos que Central notifica al operario
EV_RECIBIDA = "RECEIVED"      # Central ha recibido la petición
EV_AUTORIZADA = "AUTHORIZED"  # Riego autorizado
EV_DENEGADA = "DENIED"        # Riego denegado (el texto dice el motivo)
EV_PROGRESO = "PROGRESS"      # Riego en curso (con caudal y volumen)
EV_FINAL = "FINISHED"         # Riego terminado (resumen: volumen total)
EV_FUGA = "LEAK_STOP"         # Riego cortado por una fuga

# Acciones que Central ordena a las estaciones
ACC_INICIAR = "START"
ACC_PARAR = "STOP"
ACC_BLOQUEAR = "BLOCK"
ACC_ACTIVAR = "ACTIVATE"


def msj_pet(operario, ws, duracion):  # FO -> Central: "quiero regar en esta estación X segundos"
    return {"type": "REQUEST", "operator": operario, "ws": ws, "duration": duracion}


def msj_notif(operario, ws, evento, texto, caudal=0, volumen=0):  # Central -> FO: aviso de un paso
    return {"type": "NOTIFY", "operator": operario, "ws": ws, "event": evento,
            "text": texto, "flow": caudal, "volume": volumen}


def msj_orden(ws, accion, operario=None, duracion=None):  # Central -> Engine: orden (ws puede ser ALL)
    return {"type": "COMMAND", "ws": ws, "action": accion,
            "operator": operario, "duration": duracion}


def msj_telem(ws, operario, caudal, volumen, final=False):  # Engine -> Central: datos del riego (final=True al acabar)
    return {"type": "TELEMETRY", "ws": ws, "operator": operario,
            "flow": caudal, "volume": volumen, "final": final}

def msj_estados(estaciones):  # Central -> FO: lista de estaciones {ws: {"location", "status"}}
    return {"type": "STATIONS", "stations": estaciones}

def a_bytes(mensaje):  # Diccionario -> bytes JSON, listo para enviar por Kafka
    return json.dumps(mensaje).encode("utf-8")


def de_bytes(datos):  # bytes JSON -> diccionario (None si el mensaje no es válido)
    try:
        mensaje = json.loads(datos.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None

    if not isinstance(mensaje, dict) or "type" not in mensaje:
        return None

    return mensaje