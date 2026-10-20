# app.py
# Panel web de Central. Solo LEE el estado (state) y lo pinta; las órdenes las ejecuta commands.
#   /             -> la página con las estaciones
#   /api/estado   -> JSON con todas las estaciones (la página lo pide cada segundo)
#   /api/orden    -> recibe una orden: {"ws": "WS01" o "ALL", "accion": "iniciar|bloquear|activar", "duracion": 30}

import logging

from flask import Flask, jsonify, render_template, request

from src import state, commands

app = Flask(__name__)


@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/api/estado")
def estado():
    return jsonify(state.obt_todas())


@app.route("/api/orden", methods=["POST"])
def orden():
    datos = request.get_json(silent=True) or {}
    ws = str(datos.get("ws", "")).strip()
    accion = datos.get("accion")

    if not ws:
        return jsonify({"error": "falta la estación"}), 400

    if accion == "iniciar":
        resultado = commands.ini_riego(ws, datos.get("duracion"))
    elif accion == "bloquear":
        resultado = commands.bloq(ws)
    elif accion == "activar":
        resultado = commands.activ(ws)
    else:
        return jsonify({"error": "acción no válida"}), 400

    return jsonify(resultado)


# Arranca el panel (se lanza en un hilo desde WM_Central).
def ini_panel(puerto):
    logging.getLogger("werkzeug").setLevel(logging.ERROR)  # sin el ruido de cada petición
    print(f"[PANEL] Panel disponible en http://localhost:{puerto}")
    app.run(host="0.0.0.0", port=puerto, threaded=True, use_reloader=False)