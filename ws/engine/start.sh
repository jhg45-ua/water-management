#!/bin/sh
# Script de arranque del Engine de la Estación de Riego (WM_WS_E)

KAFKA_SERVERS=${KAFKA_SERVERS:-kafka:19092}
MONITOR_ADDR=${MONITOR_ADDR:-localhost:6001}
PROTO=${PROTO:-lrc}

echo "[ENGINE] Arrancando Engine..."
echo "[ENGINE] Conectando a Monitor en $MONITOR_ADDR | Kafka: $KAFKA_SERVERS | Protocolo: $PROTO"

exec python -u ws/engine/WM_WS_E.py "$KAFKA_SERVERS" "$MONITOR_ADDR" "$PROTO"
