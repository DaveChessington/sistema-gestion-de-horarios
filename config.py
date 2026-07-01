import os

class Config:
    # Llave secreta para JWT o sesiones
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-key-udl'
    
    # Configuración de base de datos PostgreSQL
    # Por defecto usaremos una URI de ejemplo, debe ser reemplazada en el entorno real
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://usuario:password@localhost/gestion_horarios_udl'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
