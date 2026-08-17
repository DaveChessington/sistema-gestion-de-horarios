"""Configuración exclusiva de la capa de presentación."""

import os


class Config:
    """Valores de ejecución que no incorporan lógica de negocio."""

    SECRET_KEY = os.environ.get(
        "SCHEDULE_SECRET_KEY",
        "schedule-frontend-development-key",
    )
    HOST = os.environ.get("SCHEDULE_HOST", "127.0.0.1")
    PORT = int(os.environ.get("SCHEDULE_PORT", "5004"))
    IAM_API_BASE_URL = os.environ.get(
        "IAM_API_BASE_URL",
        "http://127.0.0.1:5001/api/v1/auth",
    )
    IAM_REQUEST_TIMEOUT = float(os.environ.get("IAM_REQUEST_TIMEOUT", "5"))
    CATALOG_API_BASE_URL = os.environ.get(
        "CATALOG_API_BASE_URL",
        "http://127.0.0.1:5002/api/v1",
    )
    CATALOG_REQUEST_TIMEOUT = float(os.environ.get("CATALOG_REQUEST_TIMEOUT", "5"))
    BOOKING_API_BASE_URL = os.environ.get(
        "BOOKING_API_BASE_URL",
        "http://127.0.0.1:5003/api/v1",
    )
    BOOKING_REQUEST_TIMEOUT = float(os.environ.get("BOOKING_REQUEST_TIMEOUT", "5"))
    SESSION_COOKIE_NAME = "schedule_session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get(
        "SCHEDULE_SESSION_COOKIE_SECURE",
        "false",
    ).lower() in {"1", "true", "yes"}
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
