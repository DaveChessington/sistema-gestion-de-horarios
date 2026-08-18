FROM python:3.13-slim

WORKDIR /app

# Copiamos el contenido del contexto de build dentro de /app/booking
COPY . /app/booking

ENV PYTHONPATH=/app

RUN pip install --no-cache-dir -r /app/booking/requirements.txt
RUN chmod +x /app/booking/entrypoint.sh

WORKDIR /app/booking
ENTRYPOINT ["/bin/sh", "/app/booking/entrypoint.sh"]

#build -> docker build -t booking-service -f booking/Dockerfile ./booking
#run -> docker run -d -p 5003:5003 --name booking-service booking-service
