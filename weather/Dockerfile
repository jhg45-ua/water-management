FROM python:3.11-slim

WORKDIR /app

COPY weather/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY weather ./weather

RUN chmod +x weather/start.sh

ENV API_CENTRAL_URL=http://central:8000
ENV CITIES_FILE=/app/weather/cities.json
ENV WEATHER_INTERVAL=4

ENTRYPOINT ["/bin/sh", "weather/start.sh"]