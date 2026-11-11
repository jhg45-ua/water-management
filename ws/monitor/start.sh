#!/bin/sh
# Script de arranque del Monitor de la Estación de Riego (WM_WS_M)

PUERTO_ENGINE=${PUERTO_ENGINE:-6001}
CENTRAL_ADDR=${CENTRAL_ADDR:-central:5000}
ID_WS=${ID_WS:-WS-01}
LOCATION=${LOCATION:-"Parque Central"}
PROTO=${PROTO:-lrc}

echo "[MONITOR] Arrancando Monitor ($ID_WS en $LOCATION)..."
echo "[MONITOR] Escuchando Engine en puerto $PUERTO_ENGINE | Central: $CENTRAL_ADDR | Protocolo: $PROTO"

exec python -u ws/monitor/WM_WS_M.py "$PUERTO_ENGINE" "$CENTRAL_ADDR" "$ID_WS" "$LOCATION" "$PROTO"
