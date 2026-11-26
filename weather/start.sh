#!/bin/sh
# Script de arranque de la Oficina Meteorológica (WM_W)

API_CENTRAL_URL=${1:-${API_CENTRAL_URL:-http://central:8000}}
CITIES_FILE=${2:-${CITIES_FILE:-/app/weather/cities.json}}

echo "[WM_W] Iniciando Oficina Meteorológica hacia $API_CENTRAL_URL (ciudades: $CITIES_FILE)..."
exec python -u weather/src/WM_W.py "$API_CENTRAL_URL" "$CITIES_FILE"