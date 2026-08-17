FROM python:3.13-slim

WORKDIR /app

# Copiamos el contenido del contexto de build dentro de una carpeta "booking" para que
# el paquete importable sea /app/booking y no /app/app ni /app/config.py sueltos.
COPY . /app/booking

ENV PYTHONPATH=/app

RUN pip install --no-cache-dir -r /app/booking/requirements.txt

CMD ["python", "/app/booking/run.py"]

#build -> docker build -t booking-service -f booking/Dockerfile .
#run -> docker run -d -p 5003:5003 --name booking-service booking-service
