FROM python:3.13-slim

WORKDIR /app

# Copiamos el contenido del contexto de build dentro de /app/iam
COPY . /app/iam

ENV PYTHONPATH=/app

RUN pip install --no-cache-dir -r /app/iam/requirements.txt
RUN chmod +x /app/iam/entrypoint.sh

WORKDIR /app/iam
ENTRYPOINT ["/bin/sh", "/app/iam/entrypoint.sh"]

#build -> docker build -t iam-service -f iam/Dockerfile ./iam
#run -> docker run -d -p 5001:5001 --name iam-service iam-service
