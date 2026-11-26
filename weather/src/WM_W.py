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

class GestorCiudades:
    """Gestiona el mapeo ws_id -> ciudad con recarga en caliente desde fichero JSON y menú."""

    def __init__(self, ruta_fichero):
        self.ruta_fichero = ruta_fichero
        self._lock = threading.Lock()
        self._ciudades = {}
        self._ultimo_mtime = None
        self.recargar_si_cambio(forzar=True)

    def recargar_si_cambio(self, forzar=False):
        if not self.ruta_fichero or not os.path.exists(self.ruta_fichero):
            return False

        try:
            mtime = os.path.getmtime(self.ruta_fichero)
        except OSError:
            return False

        if not forzar and mtime == self._ultimo_mtime:
            return False

        try:
            with open(self.ruta_fichero, "r", encoding="utf-8") as f:
                datos = json.load(f)
            if not isinstance(datos, dict):
                print(f"[WM_W] Aviso: {self.ruta_fichero} debe ser un objeto JSON {{ws_id: ciudad}}.")
                return False
            limpio = {str(k).strip(): str(v).strip() for k, v in datos.items() if str(k).strip() and str(v).strip()}
        except (OSError, ValueError) as err:
            print(f"[WM_W] Error leyendo {self.ruta_fichero}: {err}")
            return False

        with self._lock:
            self._ciudades = limpio
            self._ultimo_mtime = mtime

        print(f"[WM_W] Ciudades cargadas desde {self.ruta_fichero}: {limpio}")
        return True

    def _guardar_fichero(self):
        if not self.ruta_fichero:
            return
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.ruta_fichero)), exist_ok=True)
            with open(self.ruta_fichero, "w", encoding="utf-8") as f:
                json.dump(self._ciudades, f, indent=2, ensure_ascii=False)
            self._ultimo_mtime = os.path.getmtime(self.ruta_fichero)
        except OSError as err:
            print(f"[WM_W] Aviso: no se pudo guardar {self.ruta_fichero}: {err}")

    def ciudad_para(self, ws_id, por_defecto=None):
        with self._lock:
            return self._ciudades.get(ws_id, por_defecto)

    def fijar_ciudad(self, ws_id, ciudad):
        with self._lock:
            self._ciudades[ws_id] = ciudad
            self._guardar_fichero()

    def eliminar_ciudad(self, ws_id):
        with self._lock:
            eliminada = self._ciudades.pop(ws_id, None)
            if eliminada is not None:
                self._guardar_fichero()
            return eliminada is not None

    def todas(self):
        with self._lock:
            return dict(self._ciudades)


def obtener_estaciones(api_central_url, session=None):
    cliente = session or requests
    try:
        resp = cliente.get(f"{api_central_url}/api/stations", timeout=TIMEOUT_HTTP)
        resp.raise_for_status()
        return resp.json().get("stations", [])
    except (requests.RequestException, ValueError) as err:
        print(f"[WM_W] Error consultando estaciones en {api_central_url}: {err}")
        return None


def enviar_clima(api_central_url, ws_id, clima, session=None):
    cliente = session or requests
    try:
        resp = cliente.put(f"{api_central_url}/api/weather/{ws_id}", json=clima, timeout=TIMEOUT_HTTP)
        resp.raise_for_status()
        return resp.json()
    except (requests.RequestException, ValueError) as err:
        print(f"[WM_W] Error enviando clima de {ws_id} a API_Central: {err}")
        return None


def cancelar_alerta_central(api_central_url, ws_id, session=None):
    cliente = session or requests
    try:
        resp = cliente.delete(f"{api_central_url}/api/weather/{ws_id}/alert", timeout=TIMEOUT_HTTP)
        resp.raise_for_status()
        return resp.json()
    except (requests.RequestException, ValueError) as err:
        print(f"[WM_W] Error cancelando alerta de {ws_id} en API_Central: {err}")
        return None


class OficinaMeteorologica:
    def __init__(self, api_central_url, api_key, gestor_ciudades, intervalo=INTERVALO_DEFECTO):
        self.api_central_url = api_central_url.rstrip("/")
        self.api_key = api_key
        self.gestor_ciudades = gestor_ciudades
        self.intervalo = intervalo
        self.session = requests.Session()
        self._lock = threading.Lock()
        self.ultimo_estado = {}  # ws_id -> resumen para mostrar en menú

    def ejecutar_ciclo(self):
        self.gestor_ciudades.recargar_si_cambio()
        estaciones = obtener_estaciones(self.api_central_url, self.session)
        if estaciones is None:
            return

        cache_ciudades = {}  # Evita llamadas duplicadas a OpenWeather en el mismo ciclo

        for est in estaciones:
            ws_id = est.get("ws_id")
            if not ws_id:
                continue

            clima_actual = est.get("weather") or {}
            ciudad_defecto = clima_actual.get("city") or est.get("location")
            ciudad = self.gestor_ciudades.ciudad_para(ws_id, ciudad_defecto)
            if not ciudad:
                continue

            clave_ciudad = ciudad.lower()
            if clave_ciudad not in cache_ciudades:
                cache_ciudades[clave_ciudad] = consultar_clima(ciudad, self.api_key, self.session)

            clima = cache_ciudades[clave_ciudad]
            if clima is None:
                continue

            # Copia para conservar el nombre exacto de ciudad configurado para esta WS
            payload = dict(clima, city=ciudad)
            alerta_previa = bool(clima_actual.get("alert"))
            res_put = enviar_clima(self.api_central_url, ws_id, payload, self.session)
            if res_put is None:
                continue

            estado_ws = res_put.get("status", est.get("status"))

            if payload["alert"] and not alerta_previa:
                print(f"\n[WM_W] ALERTA ACTIVADA en {ws_id} ({ciudad}): {payload['temp_c']} °C, {payload['condition']} -> {payload['reason']} (estado={estado_ws})")
            elif not payload["alert"] and alerta_previa:
                res_del = cancelar_alerta_central(self.api_central_url, ws_id, self.session)
                if res_del is not None:
                    estado_ws = res_del.get("status", estado_ws)
                print(f"\n[WM_W] ALERTA CANCELADA en {ws_id} ({ciudad}): {payload['temp_c']} °C, {payload['condition']} (estado={estado_ws})")

            with self._lock:
                self.ultimo_estado[ws_id] = {
                    "city": ciudad,
                    "temp_c": payload["temp_c"],
                    "condition": payload["condition"],
                    "alert": payload["alert"],
                    "reason": payload["reason"],
                    "status": estado_ws,
                }

    def bucle(self, evento_parada):
        print(f"[WM_W] Monitorizando clima cada {self.intervalo} s contra {self.api_central_url}...")
        while not evento_parada.is_set():
            self.ejecutar_ciclo()
            evento_parada.wait(self.intervalo)

    def mostrar_estado(self):
        with self._lock:
            snapshot = dict(self.ultimo_estado)
        overrides = self.gestor_ciudades.todas()

        if not snapshot:
            print("[WM_W] Todavía no hay estaciones monitorizadas (¿está WM_Central arrancada?).")
        else:
            print("\n--- Estado climático actual por WS ---")
            for ws_id, info in sorted(snapshot.items()):
                marca = "ALERTA" if info["alert"] else "OK"
                motivo = f" ({info['reason']})" if info["reason"] else ""
                print(f"   {ws_id} [{info['status']}] | {info['city']}: {info['temp_c']} °C, {info['condition']} -> {marca}{motivo}")

        if overrides:
            print(f"   Overrides en fichero ({self.gestor_ciudades.ruta_fichero}): {overrides}")

    def menu(self, evento_parada):
        texto = (
            "\n--- MENÚ WM_W (Oficina Meteorológica) ---\n"
            "1) Ver clima actual por WS\n"
            "2) Añadir o cambiar ciudad de una WS (en caliente)\n"
            "3) Quitar override de ciudad de una WS\n"
            "4) Forzar recarga del fichero de ciudades\n"
            "0) Salir"
        )
        while not evento_parada.is_set():
            print(texto)
            try:
                opcion = input("> ").strip()
            except EOFError:
                print("[WM_W] Sin consola interactiva: WM_W sigue monitorizando en segundo plano.")
                evento_parada.wait()
                return

            if opcion == "1":
                self.mostrar_estado()
            elif opcion == "2":
                ws_id = input("ID de la WS (ej. WS-01): ").strip()
                ciudad = input("Nueva ciudad (ej. Oslo, London, Alicante): ").strip()
                if ws_id and ciudad:
                    self.gestor_ciudades.fijar_ciudad(ws_id, ciudad)
                    print(f"[WM_W] Ciudad de {ws_id} cambiada a '{ciudad}'. Aplicando en el próximo ciclo...")
                else:
                    print("[WM_W] Debes indicar WS y ciudad.")
            elif opcion == "3":
                ws_id = input("ID de la WS a restaurar: ").strip()
                if self.gestor_ciudades.eliminar_ciudad(ws_id):
                    print(f"[WM_W] Override eliminado para {ws_id}.")
                else:
                    print(f"[WM_W] {ws_id} no tenía override configurado.")
            elif opcion == "4":
                if not self.gestor_ciudades.recargar_si_cambio(forzar=True):
                    print("[WM_W] No se pudo recargar el fichero de ciudades.")
            elif opcion == "0":
                evento_parada.set()
                return
            else:
                print("[WM_W] Opción no válida.")


def _cargar_env_local():
    """Carga variables de .env en la raíz del proyecto si no están definidas en el entorno."""
    raiz = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ruta_env = os.path.join(raiz, ".env")
    if not os.path.exists(ruta_env):
        return
    try:
        with open(ruta_env, "r", encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if not linea or linea.startswith("#") or "=" not in linea:
                    continue
                clave, valor = linea.split("=", 1)
                os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))
    except OSError:
        pass


def main():
    _cargar_env_local()

    api_central_url = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("API_CENTRAL_URL", "http://localhost:8000")
    ruta_por_defecto = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cities.json")
    ruta_ciudades = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("CITIES_FILE", ruta_por_defecto)
    api_key = os.environ.get("OPENWEATHER_API_KEY", "").strip()

    try:
        intervalo = max(1, int(os.environ.get("WEATHER_INTERVAL", INTERVALO_DEFECTO)))
    except ValueError:
        intervalo = INTERVALO_DEFECTO

    if not api_key:
        print("[WM_W] ERROR: Falta OPENWEATHER_API_KEY (defínela en .env o como variable de entorno).")
        sys.exit(1)

    gestor = GestorCiudades(ruta_ciudades)
    oficina = OficinaMeteorologica(api_central_url, api_key, gestor, intervalo=intervalo)
    evento_parada = threading.Event()

    hilo_bucle = threading.Thread(target=oficina.bucle, args=(evento_parada,), daemon=True)
    hilo_bucle.start()

    try:
        oficina.menu(evento_parada)
    except KeyboardInterrupt:
        evento_parada.set()
    finally:
        print("\n[WM_W] Oficina meteorológica detenida.")


if __name__ == "__main__":
    main()