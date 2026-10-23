#!/bin/sh
# Script de arranque del Operario de Campo (WM_FO)

KAFKA_SERVERS=${KAFKA_SERVERS:-localhost:9092}
ID_OPERADOR=${1:-${ID_OPERADOR:-OP01}}
FICHERO_SERVICIOS=${2:-$FICHERO_SERVICIOS}

if [ -n "$FICHERO_SERVICIOS" ]; then
    echo "[OPERARIO] Iniciando en Modo Fichero ($FICHERO_SERVICIOS) con ID $ID_OPERADOR..."
    exec python -u operator/src/WM_FO.py "$KAFKA_SERVERS" "$ID_OPERADOR" "$FICHERO_SERVICIOS"
else
    echo "[OPERARIO] Iniciando en Modo Manual con ID $ID_OPERADOR..."
    exec python -u operator/src/WM_FO.py "$KAFKA_SERVERS" "$ID_OPERADOR"
fi