"""
Configuración y fixtures compartidas para pruebas.
"""
import pytest
import os
from app.extensions import db
from app.models.usuario import Usuario, RolUsuario
from tests.fixtures.test_data import (
    USUARIO_ADMIN_VALIDO,
    USUARIO_DOCENTE_VALIDO,
    LOGIN_ADMIN_VALIDO,
    LOGIN_DOCENTE_VALIDO
)


@pytest.fixture(scope='function')
def app():
    """
    Crea una aplicación Flask con configuración de pruebas.
    BD SQLite en memoria para aislar de BD producción.
    """
    from flask import Flask
    from config import Config
    
    # Crear app con configuración base
    app = Flask(__name__)
    
    # Configurar BD de pruebas en memoria (SQLite)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'test-secret-key-for-jwt'
    
    # Inicializar extensiones
    db.init_app(app)
    
    # Registrar blueprints
    from app.routes.auth_routes import auth_bp
    app.register_blueprint(auth_bp)
    
    with app.app_context():
        # Importar modelos para que SQLAlchemy los registre
        from app.models.plantel import Plantel
        from app.models.usuario import Usuario
        
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """
    Cliente Flask para hacer peticiones HTTP en pruebas de integración.
    """
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    """
    CLI test runner para comandos.
    """
    return app.test_cli_runner()


@pytest.fixture(scope='function')
def init_db(app):
    """
    Inicializa la BD de pruebas con tablas.
    """
    with app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def usuario_admin(app):
    """
    Crea un usuario COORDINADOR en la BD de pruebas.
    Útil para tests que requieren autenticación.
    """
    with app.app_context():
        usuario = Usuario(
            nombre=USUARIO_ADMIN_VALIDO['nombre'],
            apellido=USUARIO_ADMIN_VALIDO['apellido'],
            correo=USUARIO_ADMIN_VALIDO['correo'],
            rol=RolUsuario.COORDINADOR,
            activo=True
        )
        usuario.set_password(USUARIO_ADMIN_VALIDO['password'])
        db.session.add(usuario)
        db.session.commit()
        return usuario


@pytest.fixture(scope='function')
def usuario_docente(app):
    """
    Crea un usuario DOCENTE en la BD de pruebas.
    """
    with app.app_context():
        usuario = Usuario(
            nombre=USUARIO_DOCENTE_VALIDO['nombre'],
            apellido=USUARIO_DOCENTE_VALIDO['apellido'],
            correo=USUARIO_DOCENTE_VALIDO['correo'],
            rol=RolUsuario.DOCENTE,
            id_plantel_asignado=1,
            activo=True
        )
        usuario.set_password(USUARIO_DOCENTE_VALIDO['password'])
        db.session.add(usuario)
        db.session.commit()
        return usuario


@pytest.fixture(scope='function')
def token_admin(app, usuario_admin):
    """
    Genera un JWT válido para un usuario COORDINADOR.
    Generado dentro del mismo contexto de app.
    """
    from app.utils.security import generate_token
    
    with app.app_context():
        # Refresh del usuario para asegurar que está en la sesión actual
        usuario = db.session.merge(usuario_admin)
        return generate_token(usuario)


@pytest.fixture(scope='function')
def token_docente(app, usuario_docente):
    """
    Genera un JWT válido para un usuario DOCENTE.
    Generado dentro del mismo contexto de app.
    """
    from app.utils.security import generate_token
    
    with app.app_context():
        # Refresh del usuario para asegurar que está en la sesión actual
        usuario = db.session.merge(usuario_docente)
        return generate_token(usuario)


@pytest.fixture(scope='function')
def usuario_inactivo(app):
    """
    Crea un usuario inactivo (activo=False).
    Útil para probar validación de usuario activo en login.
    """
    with app.app_context():
        usuario = Usuario(
            nombre="Inactivo",
            apellido="Usuario",
            correo="inactivo@udl.edu.mx",
            rol=RolUsuario.DOCENTE,
            activo=False
        )
        usuario.set_password("TestPass123!")
        db.session.add(usuario)
        db.session.commit()
        return usuario
