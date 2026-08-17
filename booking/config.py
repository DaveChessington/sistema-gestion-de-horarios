import os
from dotenv import load_dotenv

# Cargar variables de entorno desde un archivo .env si existe
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'secret-key-booking-udl'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or os.environ.get('SECRET_KEY') or 'super-secret-key-udl'
    
    # Configuración de base de datos PostgreSQL
    DB_USER = os.environ.get('DB_USER', 'postgres')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'root')
    DB_HOST = os.environ.get('DB_HOST', '127.0.0.1')
    DB_PORT = os.environ.get('DB_PORT', '5432')
    DB_NAME = os.environ.get('DB_NAME', 'gestion_horarios_udl')

    # URI para PostgreSQL con psycopg binary
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Comunicación entre servicios
    CATALOG_SERVICE_URL = os.environ.get('CATALOG_SERVICE_URL', 'http://127.0.0.1:5002')
    CATALOG_REQUEST_TIMEOUT = float(os.environ.get('CATALOG_REQUEST_TIMEOUT', '5'))
