# Se construye desde la RAÍZ del repositorio: docker build -f ws/monitor/Dockerfile -t ws-monitor .
FROM python:3.11-slim

WORKDIR /app

# Dependencias
COPY ws/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Lógica común y monitor
COPY common ./common
COPY ws/monitor ./ws/monitor
COPY ws/monitor/start.sh ./ws/monitor/start.sh
RUN chmod +x ws/monitor/start.sh

# Variables de entorno por defecto
ENV PUERTO_ENGINE=6001
ENV CENTRAL_ADDR=central:5000
ENV ID_WS=WS-01
ENV LOCATION="Parque Central"
ENV PROTO=lrc

# Puerto donde el Monitor escucha al Engine
EXPOSE 6001

ENTRYPOINT ["/bin/sh", "ws/monitor/start.sh"]
