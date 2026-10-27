#!/usr/bin/env bash
# ==============================================================================
# launch_ws.sh - Lanzador de N Water Stations en Docker
# ==============================================================================
# Uso:
#   ./launch_ws.sh <N> [start_index]   -> Lanza N estaciones (ej. ./launch_ws.sh 5)
#   ./launch_ws.sh stop                -> Detiene y elimina todas las estaciones
#   ./launch_ws.sh status              -> Muestra el estado de las estaciones
#
# Variables de entorno opcionales (útiles para conectar con AWS en PC LAB):
#   CENTRAL_ADDR="<HOST_AWS>:5000"     -> Dirección de WM_Central (def: central:5000)
#   KAFKA_SERVERS="<HOST_AWS>:9092"    -> Broker(s) Kafka (def: kafka:19092)
#   PROTO="lrc"                        -> Protocolo socket (def: lrc)
#   PUERTO_ENGINE="6001"               -> Puerto socket local del monitor (def: 6001)
#   DOCKER_NETWORK="bridge"            -> Red Docker (def: autodetección o bridge)
# ==============================================================================

set -e

# Asegurar que ejecutamos desde la raíz del proyecto
DIR_RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR_RAIZ"

IMAGE_NAME="water-management-ws"

# --- Comando: STOP ---
if [ "$1" = "stop" ] || [ "$1" = "down" ]; then
    echo "==> Buscando contenedores de estaciones (ws-*)..."
    CONTAINERS=$(docker ps -a --filter "name=^/ws-[0-9]+" --format "{{.Names}}")
    if [ -z "$CONTAINERS" ]; then
        echo "No hay contenedores de estaciones en ejecución."
    else
        echo "Deteniendo y eliminando contenedores:"
        echo "$CONTAINERS"
        docker rm -f $CONTAINERS
        echo "Todas las estaciones han sido detenidas."
    fi
    exit 0
fi

# --- Comando: STATUS ---
if [ "$1" = "status" ] || [ "$1" = "ps" ]; then
    docker ps --filter "name=^/ws-[0-9]+" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    exit 0
fi

# --- Validación de argumentos para lanzar estaciones ---
NUM_STATIONS=${1:-3}
START_INDEX=${2:-1}

# Validar que los parámetros sean números enteros positivos
if ! [[ "$NUM_STATIONS" =~ ^[0-9]+$ ]] || [ "$NUM_STATIONS" -le 0 ]; then
    echo "Error: El número de estaciones debe ser un entero positivo."
    echo "Uso: $0 <número_de_estaciones> [índice_inicial]"
    echo "     $0 stop"
    echo "     $0 status"
    exit 1
fi

if ! [[ "$START_INDEX" =~ ^[0-9]+$ ]] || [ "$START_INDEX" -le 0 ]; then
    echo "Error: El índice inicial debe ser un entero positivo."
    exit 1
fi

END_INDEX=$((START_INDEX + NUM_STATIONS - 1))

# --- Configuración de conexión (Personalizable por variables de entorno) ---
CENTRAL_ADDR="${CENTRAL_ADDR:-central:5000}"
KAFKA_SERVERS="${KAFKA_SERVERS:-kafka:19092}"
PROTO="${PROTO:-lrc}"
PUERTO_ENGINE="${PUERTO_ENGINE:-6001}"
DOCKER_NETWORK="${DOCKER_NETWORK:-}"

# --- 1. Detección / Selección de la red Docker ---
if [ -n "$DOCKER_NETWORK" ]; then
    NETWORK="$DOCKER_NETWORK"
else
    # Intenta obtener la red del contenedor central local si existe
    NETWORK=$(docker inspect -f '{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{end}}' central 2>/dev/null || true)

    if [ -z "$NETWORK" ]; then
        CENTRAL_ID=$(docker ps --filter "name=central" -q | head -n 1)
        if [ -n "$CENTRAL_ID" ]; then
            NETWORK=$(docker inspect -f '{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{end}}' "$CENTRAL_ID" 2>/dev/null || true)
        fi
    fi

    if [ -z "$NETWORK" ]; then
        if docker network inspect water-management_default >/dev/null 2>&1; then
            NETWORK="water-management_default"
        else
            # Si conectamos a AWS o remoto y no hay red compose local, usamos la red estándar bridge
            NETWORK="bridge"
        fi
    fi
fi

# --- 2. Comprobar / Construir la imagen Docker ---
if ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
    echo "==> Construyendo imagen Docker: $IMAGE_NAME..."
    docker build -t "$IMAGE_NAME" -f ws/Dockerfile .
else
    echo "==> Usando imagen existente: $IMAGE_NAME"
fi

echo "============================================================"
echo "Lanzando $NUM_STATIONS estación(es) de agua (de WS-$(printf "%02d" $START_INDEX) a WS-$(printf "%02d" $END_INDEX))"
echo "Destino Central : $CENTRAL_ADDR"
echo "Destino Kafka   : $KAFKA_SERVERS"
echo "Protocolo       : $PROTO"
echo "Red Docker      : $NETWORK"
echo "============================================================"

# --- 3. Bucle de lanzamiento de contenedores ---
for ((i = START_INDEX; i <= END_INDEX; i++)); do
    ID_PAD=$(printf "%02d" "$i")
    CONTAINER_NAME="ws-$ID_PAD"
    ID_WS="WS-$ID_PAD"
    LOCATION="Sector $ID_PAD"

    # Si ya existe un contenedor con ese nombre, eliminarlo
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo "[-] Reemplazando contenedor previo $CONTAINER_NAME..."
        docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1
    fi

    # Lanzar contenedor detached con stdin interactivo habilitado (-dit)
    docker run -dit \
        --name "$CONTAINER_NAME" \
        --network "$NETWORK" \
        -e ID_WS="$ID_WS" \
        -e LOCATION="$LOCATION" \
        -e CENTRAL_ADDR="$CENTRAL_ADDR" \
        -e KAFKA_SERVERS="$KAFKA_SERVERS" \
        -e PROTO="$PROTO" \
        -e PUERTO_ENGINE="$PUERTO_ENGINE" \
        --restart unless-stopped \
        "$IMAGE_NAME" >/dev/null

    echo " [✓] $CONTAINER_NAME iniciado -> ID: $ID_WS | Ubicación: '$LOCATION'"
done

echo "============================================================"
echo "¡$NUM_STATIONS estaciones lanzadas correctamente!"
echo ""
echo "Comandos útiles:"
echo "  - Ver logs de una estación:     docker logs -f ws-01"
echo "  - Simular avería (teclado 'k'): docker attach ws-01 (Salir: Ctrl+P, Ctrl+Q)"
echo "  - Ver estado de estaciones:     ./launch_ws.sh status"
echo "  - Detener todas las estaciones: ./launch_ws.sh stop"
echo "============================================================"
