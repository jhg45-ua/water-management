#!/bin/sh
# Script de arranque de la Estación de Riego (Monitor + Engine)

PUERTO_ENGINE=${PUERTO_ENGINE:-6001}
CENTRAL_ADDR=${CENTRAL_ADDR:-localhost:5000}
ID_WS=${ID_WS:-WS-01}
LOCATION=${LOCATION:-"Parque Central"}
PROTO=${PROTO:-lrc}
KAFKA_SERVERS=${KAFKA_SERVERS:-localhost:9092}

echo "[ESTACION] Arrancando Monitor ($ID_WS en $LOCATION)..."
python -u ws/monitor/WM_WS_M.py "$PUERTO_ENGINE" "$CENTRAL_ADDR" "$ID_WS" "$LOCATION" "$PROTO" &
MONITOR_PID=$!

# Esperamos un segundo a que el Monitor abra su socket local
sleep 1

echo "[ESTACION] Arrancando Engine (conectado al teclado para simular averías)..."
# Usamos exec para que la consola interactiva (stdin/stdout) quede enlazada al Engine
exec python -u ws/engine/WM_WS_E.py "$KAFKA_SERVERS" "localhost:$PUERTO_ENGINE" "$PROTO"