from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Inicializamos SQLAlchemy y Migrate sin la app por ahora (patrón factory)
db = SQLAlchemy()
migrate = Migrate()
