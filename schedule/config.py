"""Configuración exclusiva de la capa de presentación."""

import os


class Config:
    """Valores de ejecución que no incorporan lógica de negocio."""

    HOST = os.environ.get("SCHEDULE_HOST", "127.0.0.1")
    PORT = int(os.environ.get("SCHEDULE_PORT", "5004"))
    DEBUG = os.environ.get("SCHEDULE_DEBUG", "false").lower() in {
        "1",
        "true",
        "yes",
    }
    OPEN_BROWSER = os.environ.get("SCHEDULE_OPEN_BROWSER", "true").lower() in {
        "1",
        "true",
        "yes",
    }
