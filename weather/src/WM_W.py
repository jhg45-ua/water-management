import json
import os
import sys
import threading
import time

import requests

OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
INTERVALO_DEFECTO = 4  # segundos (requisito del enunciado)
TIMEOUT_HTTP = 5
CONDICIONES_LLUVIA = {"Rain", "Drizzle", "Thunderstorm"}


def evaluar_alerta(datos_ow):
    """
    Analiza la respuesta JSON de OpenWeather (Current weather data, units=metric)
    y devuelve (temp_c, condition, alert, reason).
    Condiciones adversas: temperatura < 0 °C (< 273.15 K) o lluvia.
    """
    temp_c = round(float(datos_ow["main"]["temp"]), 2)
    weather_list = datos_ow.get("weather") or []
    principal = weather_list[0] if weather_list else {}
    condicion = principal.get("main", "Unknown")
    weather_id = int(principal.get("id", 0) or 0)

    hay_lluvia = (
        condicion in CONDICIONES_LLUVIA
        or (200 <= weather_id <= 531)
        or bool(datos_ow.get("rain"))
    )

    motivos = []
    if temp_c < 0.0:
        motivos.append(f"Temperatura inferior a 0 °C ({temp_c} °C)")
    if hay_lluvia:
        desc = principal.get("description") or condicion
        motivos.append(f"Lluvia detectada ({desc})")

    alerta = len(motivos) > 0
    motivo = "; ".join(motivos) if alerta else None
    return temp_c, condicion, alerta, motivo


def consultar_clima(ciudad, api_key, session=None):
    """
    Consulta OpenWeather para una ciudad y devuelve dict con
    {city, temp_c, condition, alert, reason} o None si falla.
    """
    cliente = session or requests
    try:
        resp = cliente.get(
            OPENWEATHER_URL,
            params={"q": ciudad, "appid": api_key, "units": "metric"},
            timeout=TIMEOUT_HTTP,
        )
        if resp.status_code == 401:
            print("[WM_W] Error OpenWeather (401): API key inválida o aún no activada.")
            return None
        if resp.status_code == 404:
            print(f"[WM_W] Error OpenWeather (404): ciudad '{ciudad}' no encontrada.")
            return None
        resp.raise_for_status()
        datos = resp.json()
    except requests.RequestException as err:
        print(f"[WM_W] Error de red consultando OpenWeather para '{ciudad}': {err}")
        return None
    except (ValueError, KeyError) as err:
        print(f"[WM_W] Respuesta inesperada de OpenWeather para '{ciudad}': {err}")
        return None

    temp_c, condicion, alerta, motivo = evaluar_alerta(datos)
    return {
        "city": ciudad,
        "temp_c": temp_c,
        "condition": condicion,
        "alert": alerta,
        "reason": motivo,
    }

