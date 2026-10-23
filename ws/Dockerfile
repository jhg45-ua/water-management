FROM python:3.11-slim

WORKDIR /app

# Instalamos dependencias
COPY ws/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos la lógica común y el módulo ws
COPY common ./common
COPY ws ./ws

RUN chmod +x ws/start.sh

# Variables de entorno por defecto
ENV PUERTO_ENGINE=6001
ENV CENTRAL_ADDR=localhost:5000
ENV ID_WS=WS-01
ENV LOCATION="Parque Central"
ENV PROTO=lrc
ENV KAFKA_SERVERS=localhost:9092

ENTRYPOINT ["/bin/sh", "ws/start.sh"]