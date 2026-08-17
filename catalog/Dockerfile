FROM python:3.13-slim

WORKDIR /app

# Copiamos el contenido del contexto de build dentro de /app/catalog
COPY . /app/catalog

ENV PYTHONPATH=/app

RUN pip install --no-cache-dir -r /app/catalog/requirements.txt
RUN chmod +x /app/catalog/entrypoint.sh

WORKDIR /app/catalog
ENTRYPOINT ["/bin/sh", "/app/catalog/entrypoint.sh"]

#build -> docker build -t catalog-service -f catalog/Dockerfile ./catalog
#run -> docker run -d -p 5002:5002 --name catalog-service catalog-service