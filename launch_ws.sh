#!/usr/bin/env bash
# ==============================================================================
# launch_ws.sh - Lanzador de N Water Stations en Docker (Contenedores separados)
# ==============================================================================
# Cada estación se compone de DOS contenedores independientes:
#   - ws-<ID>-monitor: Monitor (WM_WS_M) conectado a Central por socket
#   - ws-<ID>-engine:  Engine (WM_WS_E) conectado al Monitor y a Kafka
#
# Uso:
#   ./launch_ws.sh <N> [start_index]   -> Lanza N estaciones (ej. ./launch_ws.sh 3)
#   ./launch_ws.sh stop                -> Detiene y elimina todas las estaciones
#   ./launch_ws.sh status              -> Muestra el estado de las estaciones
#
# Variables de entorno opcionales (útiles para conectar con AWS en PC LAB):
#   CENTRAL_ADDR="<HOST_AWS>:5000"     -> Dirección de WM_Central (def: central:5000)
#   KAFKA_SERVERS="<HOST_AWS>:9092"    -> Broker(s) Kafka (def: kafka:19092)
#   PROTO="lrc"                        -> Protocolo socket (def: lrc)
#   PUERTO_ENGINE="6001"               -> Puerto socket local del monitor (def: 6001)
#   DOCKER_NETWORK="mi_red"            -> Red Docker (def: autodetección o water-management_net)
# ==============================================================================

set -e

# Asegurar que ejecutamos desde la raíz del proyecto
DIR_RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR_RAIZ"

IMAGE_MONITOR="${IMAGE_MONITOR:-ws-monitor}"
IMAGE_ENGINE="${IMAGE_ENGINE:-ws-engine}"

# Cargar variables desde .env si existe en la raíz
if [ -f "$DIR_RAIZ/.env" ]; then
    set -a
    . "$DIR_RAIZ/.env"
    set +a
fi

ACTION=""
NUM_STATIONS=""
START_INDEX=""
REMOTE_HOST=""

while [ $# -gt 0 ]; do
    case "$1" in
        stop|down)
            ACTION="stop"
            shift
            ;;
        status|ps)
            ACTION="status"
            shift
            ;;
        --host=*)
            REMOTE_HOST="${1#*=}"
            shift
            ;;
        --host|-h)
            REMOTE_HOST="$2"
            shift 2
            ;;
        *)
            if [ -z "$NUM_STATIONS" ] && [[ "$1" =~ ^[0-9]+$ ]]; then
                NUM_STATIONS="$1"
            elif [ -z "$START_INDEX" ] && [[ "$1" =~ ^[0-9]+$ ]]; then
                START_INDEX="$1"
            else
                echo "Error: Argumento no reconocido '$1'."
                echo "Uso: $0 [número_de_estaciones] [índice_inicial] [--host <IP>]"
                echo "     $0 stop"
                echo "     $0 status"
                exit 1
            fi
            shift
            ;;
    esac
done

# --- Comando: STOP ---
if [ "$ACTION" = "stop" ]; then
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
if [ "$ACTION" = "status" ]; then
    docker ps -a --filter "name=^/ws-[0-9]+" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    exit 0
fi

# --- Valores por defecto para estaciones si no se indicaron ---
NUM_STATIONS=${NUM_STATIONS:-3}
START_INDEX=${START_INDEX:-1}

# Validar que los parámetros sean enteros positivos
if [ "$NUM_STATIONS" -le 0 ]; then
    echo "Error: El número de estaciones debe ser un entero positivo."
    exit 1
fi

if [ "$START_INDEX" -le 0 ]; then
    echo "Error: El índice inicial debe ser un entero positivo."
    exit 1
fi

END_INDEX=$((START_INDEX + NUM_STATIONS - 1))

# Si se pasó --host explícito por argumento:
if [ -n "$REMOTE_HOST" ]; then
    CENTRAL_ADDR="$REMOTE_HOST:5000"
    KAFKA_SERVERS="$REMOTE_HOST:9092"
# Si se definió HOST_IP o PUBLIC_IP y no CENTRAL_ADDR directamente:
elif [ -n "$HOST_IP" ]; then
    CENTRAL_ADDR="${CENTRAL_ADDR:-$HOST_IP:5000}"
    KAFKA_SERVERS="${KAFKA_SERVERS:-$HOST_IP:9092}"
elif [ -n "$PUBLIC_IP" ] && [ "$PUBLIC_IP" != "localhost" ]; then
    CENTRAL_ADDR="${CENTRAL_ADDR:-$PUBLIC_IP:5000}"
    KAFKA_SERVERS="${KAFKA_SERVERS:-$PUBLIC_IP:9092}"
fi

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
            # Para interconexión entre Engine y Monitor por DNS de Docker, se requiere una red de usuario
            NETWORK="water-management_net"
            if ! docker network inspect "$NETWORK" >/dev/null 2>&1; then
                echo "==> Creando red Docker '$NETWORK' para comunicación interna de estaciones..."
                docker network create "$NETWORK" >/dev/null
            fi
        fi
    fi
fi

# --- 2. Comprobar / Construir las imágenes Docker ---
if ! docker image inspect "$IMAGE_MONITOR" >/dev/null 2>&1; then
    echo "==> Construyendo imagen Docker para Monitor: $IMAGE_MONITOR..."
    docker build -t "$IMAGE_MONITOR" -f ws/monitor/Dockerfile .
else
    echo "==> Usando imagen existente de Monitor: $IMAGE_MONITOR"
fi

if ! docker image inspect "$IMAGE_ENGINE" >/dev/null 2>&1; then
    echo "==> Construyendo imagen Docker para Engine: $IMAGE_ENGINE..."
    docker build -t "$IMAGE_ENGINE" -f ws/engine/Dockerfile .
else
    echo "==> Usando imagen existente de Engine: $IMAGE_ENGINE"
fi

TOTAL_CONTAINERS=$((NUM_STATIONS * 2))

echo "============================================================"
echo "Lanzando $NUM_STATIONS estación(es) ($TOTAL_CONTAINERS contenedores: Monitor + Engine por separado)"
echo "Rango de estaciones: WS-$(printf "%02d" $START_INDEX) a WS-$(printf "%02d" $END_INDEX)"
echo "Destino Central    : $CENTRAL_ADDR"
echo "Destino Kafka      : $KAFKA_SERVERS"
echo "Protocolo          : $PROTO"
echo "Red Docker         : $NETWORK"
echo "============================================================"

if [ "$CENTRAL_ADDR" = "central:5000" ] && [ -z "$(docker ps -q --filter "name=^/central$" 2>/dev/null)" ]; then
    echo "⚠️  AVISO: No se detecta el contenedor local 'central'."
    echo "   Las estaciones están buscando 'central:5000'. Si estás usando AWS (ej. 51.95.62.175):"
    echo "     ./launch_ws.sh $NUM_STATIONS --host=51.95.62.175"
    echo "   o define las variables en un archivo .env (PUBLIC_IP=51.95.62.175)"
    echo "============================================================"
fi

# --- 3. Bucle de lanzamiento de contenedores ---
for ((i = START_INDEX; i <= END_INDEX; i++)); do
    ID_PAD=$(printf "%02d" "$i")
    ID_WS="WS-$ID_PAD"
    LOCATION="Sector $ID_PAD"
    MONITOR_NAME="ws-$ID_PAD-monitor"
    ENGINE_NAME="ws-$ID_PAD-engine"

    # Si ya existen contenedores previos con esos nombres, eliminarlos
    for cname in "$MONITOR_NAME" "$ENGINE_NAME"; do
        if docker ps -a --format '{{.Names}}' | grep -q "^${cname}$"; then
            echo "[-] Reemplazando contenedor previo $cname..."
            docker rm -f "$cname" >/dev/null 2>&1
        fi
    done

    # 3.1. Lanzar Monitor (Servicio de supervisión y enlace con Central)
    docker run -d \
        --name "$MONITOR_NAME" \
        --network "$NETWORK" \
        -e ID_WS="$ID_WS" \
        -e LOCATION="$LOCATION" \
        -e CENTRAL_ADDR="$CENTRAL_ADDR" \
        -e PUERTO_ENGINE="$PUERTO_ENGINE" \
        -e PROTO="$PROTO" \
        --restart unless-stopped \
        "$IMAGE_MONITOR" >/dev/null

    # 3.2. Lanzar Engine (Contenedor interactivo conectado a Monitor y Kafka)
    docker run -dit \
        --name "$ENGINE_NAME" \
        --network "$NETWORK" \
        -e KAFKA_SERVERS="$KAFKA_SERVERS" \
        -e MONITOR_ADDR="${MONITOR_NAME}:${PUERTO_ENGINE}" \
        -e PROTO="$PROTO" \
        --restart unless-stopped \
        "$IMAGE_ENGINE" >/dev/null

    echo " [✓] Estación $ID_WS iniciada:"
    echo "     - Monitor : $MONITOR_NAME (Central: $CENTRAL_ADDR | Escucha Engine: $PUERTO_ENGINE)"
    echo "     - Engine  : $ENGINE_NAME  (Conectado a: $MONITOR_NAME:$PUERTO_ENGINE | Kafka: $KAFKA_SERVERS)"
done

echo "============================================================"
echo "¡$NUM_STATIONS estaciones ($TOTAL_CONTAINERS contenedores) lanzadas correctamente!"
echo ""
echo "Comandos útiles para evaluación:"
echo "  - Ver logs del Monitor:         docker logs -f ws-01-monitor"
echo "  - Ver logs del Engine:          docker logs -f ws-01-engine"
echo "  - Simular avería (teclado 'k'): docker attach ws-01-engine (Salir: Ctrl+P, Ctrl+Q)"
echo "  - Simular caída del Engine:     docker stop ws-01-engine (Detección de LEAK en Central)"
echo "  - Reactivar el Engine:          docker start ws-01-engine (Recuperación automática)"
echo "  - Ver estado de estaciones:     ./launch_ws.sh status"
echo "  - Detener todas las estaciones: ./launch_ws.sh stop"
echo "============================================================"
