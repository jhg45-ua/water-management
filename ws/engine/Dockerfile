# Se construye desde la RAÍZ del repositorio: docker build -f ws/engine/Dockerfile -t ws-engine .
FROM python:3.11-slim

WORKDIR /app

# Dependencias
COPY ws/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Lógica común y engine
COPY common ./common
COPY ws/engine ./ws/engine
COPY ws/engine/start.sh ./ws/engine/start.sh
RUN chmod +x ws/engine/start.sh

# Variables de entorno por defecto
ENV KAFKA_SERVERS=kafka:19092
ENV MONITOR_ADDR=localhost:6001
ENV PROTO=lrc

ENTRYPOINT ["/bin/sh", "ws/engine/start.sh"]
