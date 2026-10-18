
from common import messages
from src import state, kafka_handlers


def _aplicar(ws, funcion, texto):
    if ws.upper() == messages.TODAS:
        destinos = list(state.obt_todas())
    elif state.hay_estac(ws):
        destinos = [ws]
    else:
        print(f"[ORDEN] La estación {ws} no existe")
        return {ws: False}

    resultados = {}

    for destino in destinos:
        hecho = funcion(destino)
        resultados[destino] = hecho
        print(f"[ORDEN] {destino}: {texto} -> {'hecho' if hecho else 'no se ha podido'}")

    return resultados


def ini_riego(ws, duracion):
    return _aplicar(ws, lambda destino: kafka_handlers.iniciar_riego_central(destino, duracion), "iniciar riego")


def bloq(ws):
    return _aplicar(ws, kafka_handlers.bloquear_estacion, "bloquear")


def activ(ws):
    return _aplicar(ws, kafka_handlers.activar_estacion, "activar")


def ver_estaciones():
    estaciones = state.obt_todas()

    if not estaciones:
        print("[ORDEN] No hay estaciones registradas")

    for ws, datos in estaciones.items():
        print(f"   {ws} - {datos['location']} - {datos['status']} - {datos['flow']} L/min, {datos['volume']} L")


def menu_cons():
    texto = "\n1) Iniciar riego  2) Bloquear  3) Activar  4) Ver estaciones  0) Cerrar menú"

    while True:
        print(texto)

        try:
            opcion = input("> ").strip()

            if opcion == "1":
                ini_riego(input("Estación (id o ALL): ").strip(), input("Duración (s): ").strip())
            elif opcion == "2":
                bloq(input("Estación (id o ALL): ").strip())
            elif opcion == "3":
                activ(input("Estación (id o ALL): ").strip())
            elif opcion == "4":
                ver_estaciones()
            elif opcion == "0":
                print("[ORDEN] Menú cerrado (Central sigue en marcha)")
                return
            else:
                print("[ORDEN] Opción no válida")

        except EOFError:
            print("[ORDEN] Sin consola disponible, menú desactivado")
            return
