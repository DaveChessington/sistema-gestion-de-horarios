FROM python:3.13-slim

WORKDIR /app

# Copiamos el contenido del contexto de build dentro de /app/schedule
COPY . /app/schedule

ENV PYTHONPATH=/app
ENV SCHEDULE_HOST=0.0.0.0
ENV SCHEDULE_PORT=5004

RUN pip install --no-cache-dir -r /app/schedule/requirements.txt

WORKDIR /app/schedule

EXPOSE 5004

CMD ["python", "run.py"]
