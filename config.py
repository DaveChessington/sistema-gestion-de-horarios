import os

class Config:
    # Llave secreta para JWT o sesiones
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-key-udl'
    
    # Configuración de base de datos PostgreSQL
    user = os.environ.get('DB_USER')
    password = os.environ.get('DB_PASSWORD')
    host = os.environ.get('HOST')
    port = os.environ.get('PORT')
    db_name = os.environ.get('DB_NAME')
    """    
    if all([user, password, host, port, db_name]):
        SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db_name}"
    else:
        SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg://postgres:root@127.0.0.1:5432/gestion_horarios_UDL'
    print(SQLALCHEMY_DATABASE_URI)"""
    SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg://postgres:root@127.0.0.1:5432/gestion_horarios_udl'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
