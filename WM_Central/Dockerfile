# Se construye desde la RAÍZ del repositorio:  docker build -f WM_Central/Dockerfile -t wm-central .
FROM python:3.11-slim

WORKDIR /app

COPY WM_Central/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY common ./common
COPY WM_Central ./WM_Central

# La BD se guarda en /data (en Railway, montar ahí un volumen)
RUN mkdir -p /data
ENV KAFKA_SERVERS=kafka:19092
ENV DB_PATH=/data/wm.db
ENV PORT=8080

WORKDIR /app/WM_Central

# 5000 = sockets de los Monitores, 8080 = panel web
EXPOSE 5000 8080

CMD ["sh", "-c", "python -u WM_Central.py 5000 $KAFKA_SERVERS $DB_PATH"]