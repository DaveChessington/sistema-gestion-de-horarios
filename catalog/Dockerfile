FROM python:3.13-slim

WORKDIR /app

# Copiamos el contenido del contexto de build dentro de una carpeta "catalog" para que
# el paquete importable sea /app/catalog y no /app/app ni /app/config.py sueltos.
COPY . /app/catalog

ENV PYTHONPATH=/app

RUN pip install -r /app/catalog/requirements.txt

CMD ["python", "/app/catalog/run.py"]

#build -> docker build -t gestion-horarios .
#run -> docker run -d -p 5000:5000 --name gestion-horarios gestion-horarios