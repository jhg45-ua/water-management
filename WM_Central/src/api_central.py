# api_central.py
# API REST de la Central (P2). Consumida por el Front y por WM_W (oficina meteorológica).

import logging

from flask import Flask, jsonify, request

from common import messages
from database import db
from src import commands, kafka_handlers, state

app = Flask(__name__)


@app.after_request
def añadir_cors(respuesta):  # Permite peticiones desde el Front (otro origen/puerto)
    respuesta.headers["Access-Control-Allow-Origin"] = "*"
    respuesta.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    respuesta.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return respuesta


def _ip_cliente():
    return request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()


# --- Consultas de estado (Front y WM_W) ---

@app.route("/api/stations", methods=["GET"])
def listar_estaciones():
    return jsonify({"stations": state.obt_todas_api()}), 200


@app.route("/api/stations/<ws_id>", methods=["GET"])
def detalle_estacion(ws_id):
    estacion = state.obt_estacion_api(ws_id)
    if estacion is None:
        return jsonify({"error": f"Station {ws_id} not found"}), 404
    return jsonify(estacion), 200


@app.route("/api/operators", methods=["GET"])
def listar_operarios():
    # Cruzamos los operarios de BD con los riegos activos en memoria
    activos_por_op = {r["operator_id"]: r["ws_id"] for r in state.obt_riegos_api()}
    operarios = [
        {
            "operator_id": op["id"],
            "name": op["name"],
            "active_ws": activos_por_op.get(op["id"]),
        }
        for op in db.list_opers()
    ]
    return jsonify({"operators": operarios}), 200


@app.route("/api/waterings", methods=["GET"])
def listar_riegos():
    return jsonify({"waterings": state.obt_riegos_api()}), 200


@app.route("/api/audit", methods=["GET"])
def listar_auditoria():
    source = request.args.get("source")
    level = request.args.get("level")
    try:
        limit = max(1, min(500, int(request.args.get("limit", 50))))
    except ValueError:
        return jsonify({"error": "Invalid limit parameter"}), 400

    eventos = db.list_auditoria(limit=limit, source=source, level=level)
    return jsonify({"events": eventos}), 200


# --- Clima y alertas meteorológicas (WM_W) ---

@app.route("/api/weather/<ws_id>", methods=["PUT"])
def actualizar_clima(ws_id):
    datos = request.get_json(silent=True) or {}
    requeridos = ("city", "temp_c", "condition", "alert")
    if any(campo not in datos for campo in requeridos):
        return jsonify({"error": "Missing required weather fields"}), 400

    try:
        temp_c = float(datos["temp_c"])
    except (TypeError, ValueError):
        return jsonify({"error": "temp_c must be a number"}), 400

    ciudad = str(datos["city"]).strip()
    condicion = str(datos["condition"]).strip()
    alerta = bool(datos["alert"])
    motivo = datos.get("reason")

    resultado = state.aplicar_clima(ws_id, ciudad, temp_c, condicion, alerta, motivo)
    if resultado is None:
        return jsonify({"error": f"Station {ws_id} not found"}), 404

    if resultado["send_block"]:
        kafka_handlers.ordenar(ws_id, messages.ACC_BLOQUEAR)

    if alerta:
        detalle = f"{ws_id} ({ciudad}): {temp_c}C, {condicion} - {motivo or 'alerta climática'}"
        db.reg_auditoria("WM_W", "WM_W", _ip_cliente(), "WEATHER_ALERT", "WARNING", detalle)

    return jsonify({
        "ws_id": resultado["ws_id"],
        "weather_alert": resultado["weather_alert"],
        "status": resultado["status"],
        "pending_weather_stop": resultado["pending_weather_stop"],
    }), 200


@app.route("/api/weather/<ws_id>/alert", methods=["DELETE"])
def cancelar_alerta(ws_id):
    resultado = state.cancelar_alerta_clima(ws_id)
    if resultado is None:
        return jsonify({"error": f"Station {ws_id} not found"}), 404

    if resultado["send_activate"]:
        kafka_handlers.ordenar(ws_id, messages.ACC_ACTIVAR)

    db.reg_auditoria(
        "WM_W", "WM_W", _ip_cliente(), "WEATHER_CLEAR", "INFO",
        f"{ws_id}: alerta climática cancelada (estado={resultado['status']})",
    )

    return jsonify({
        "ws_id": resultado["ws_id"],
        "weather_alert": False,
        "status": resultado["status"],
    }), 200


# --- Órdenes manuales desde el Front ---

@app.route("/api/stations/<ws_id>/commands", methods=["POST"])
def ejecutar_orden(ws_id):
    if not state.hay_estac(ws_id):
        return jsonify({"error": f"Station {ws_id} not found"}), 404

    datos = request.get_json(silent=True) or {}
    accion = str(datos.get("action", "")).strip().lower()

    if accion == "start":
        res = commands.ini_riego(ws_id, datos.get("duration"))
        ok = bool(res.get(ws_id))
    elif accion == "block":
        res = commands.bloq(ws_id)
        ok = bool(res.get(ws_id))
    elif accion == "activate":
        res = commands.activ(ws_id)
        ok = bool(res.get(ws_id))
    elif accion == "revoke_key":
        ok = state.revocar_clave(ws_id)
        if ok:
            kafka_handlers.ordenar(ws_id, messages.ACC_BLOQUEAR)
            db.reg_auditoria("API_CENTRAL", "ADMIN", _ip_cliente(), "KEY_REVOKED", "SECURITY", f"Clave revocada para {ws_id}")
    else:
        return jsonify({"error": "Invalid action"}), 400

    if accion != "revoke_key":
        db.reg_auditoria("API_CENTRAL", "ADMIN", _ip_cliente(), f"COMMAND_{accion.upper()}", "INFO", f"{ws_id}: ok={ok}")

    return jsonify({
        "ws_id": ws_id,
        "action": accion,
        "ok": ok,
        "message": "Command executed" if ok else "Command could not be executed",
    }), 200


# Arranca API_Central en un hilo desde WM_Central.py
def ini_api(puerto=8000):
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    print(f"[API_CENTRAL] API REST disponible en http://localhost:{puerto}")
    app.run(host="0.0.0.0", port=puerto, threaded=True, use_reloader=False)