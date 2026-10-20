FROM python:3.11-slim

WORKDIR /app

# Instalamos dependencias
COPY operator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos la lógica común y el módulo operator
COPY common ./common
COPY operator ./operator

RUN chmod +x operator/start.sh

# Variables de entorno por defecto
ENV KAFKA_SERVERS=localhost:9092
ENV ID_OPERADOR=OP01
ENV FICHERO_SERVICIOS=""

ENTRYPOINT ["/bin/sh", "operator/start.sh"]