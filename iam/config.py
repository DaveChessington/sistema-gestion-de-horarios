import os

class Config:
    # Llave secreta para JWT o sesiones
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-key-udl'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or SECRET_KEY

    # Configuración de base de datos PostgreSQL
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        SQLALCHEMY_DATABASE_URI = db_url
    else:
        user = os.environ.get('DB_USER') or 'postgres'
        password = os.environ.get('DB_PASSWORD') or 'root'
        host = os.environ.get('DB_HOST') or os.environ.get('HOST') or '127.0.0.1'
        port = os.environ.get('DB_PORT') or os.environ.get('PORT') or '5432'
        db_name = os.environ.get('DB_NAME') or 'gestion_horarios_udl'
        SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db_name}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CATALOG_API_BASE_URL = os.environ.get('CATALOG_API_BASE_URL') or 'http://127.0.0.1:5002/api/v1'
