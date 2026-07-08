"""
Pruebas unitarias del servicio AuthService.
Valida reglas de negocio de registro y login.
"""
import pytest
from app.services.auth_service import AuthService
from app.models.usuario import Usuario, RolUsuario
from app.extensions import db
from tests.fixtures.test_data import (
    USUARIO_ADMIN_VALIDO,
    USUARIO_DOCENTE_VALIDO,
    USUARIO_ALUMNO_VALIDO,
    USUARIO_CORREO_DUPLICADO,
    USUARIO_ROL_INVALIDO,
    USUARIO_PASSWORD_VACIA,
    LOGIN_ADMIN_VALIDO,
    LOGIN_DOCENTE_VALIDO,
    LOGIN_PASSWORD_INCORRECTO,
    LOGIN_CORREO_INEXISTENTE,
)


@pytest.mark.unit
class TestAuthServiceRegister:
    """Pruebas unitarias para el registro de usuarios."""

    # ==========================================
    # CASOS NORMALES (S1-S2)
    # ==========================================

    def test_registro_exitoso_coordinador(self, app):
        """
        S1: Registro exitoso de un COORDINADOR.
        CASO NORMAL: todos los campos válidos.
        """
        with app.app_context():
            resultado = AuthService.register_user(USUARIO_ADMIN_VALIDO)
            
            assert resultado['success'] is True
            assert resultado['status_code'] == 201
            assert 'data' in resultado
            assert resultado['data']['correo'] == USUARIO_ADMIN_VALIDO['correo']
            assert resultado['data']['rol'] == RolUsuario.COORDINADOR
            
            # Verificar que se guardó en BD
            usuario = Usuario.query.filter_by(
                correo=USUARIO_ADMIN_VALIDO['correo']
            ).first()
            assert usuario is not None
            assert usuario.nombre == USUARIO_ADMIN_VALIDO['nombre']

    def test_registro_exitoso_docente(self, app):
        """
        S2: Registro exitoso de un DOCENTE.
        CASO NORMAL: con id_plantel_asignado.
        """
        with app.app_context():
            resultado = AuthService.register_user(USUARIO_DOCENTE_VALIDO)
            
            assert resultado['success'] is True
            assert resultado['status_code'] == 201
            assert resultado['data']['rol'] == RolUsuario.DOCENTE
            assert resultado['data']['id_plantel_asignado'] == 1

    def test_registro_exitoso_alumno(self, app):
        """
        CASO NORMAL: Registro exitoso de ALUMNO sin plantel.
        """
        with app.app_context():
            resultado = AuthService.register_user(USUARIO_ALUMNO_VALIDO)
            
            assert resultado['success'] is True
            assert resultado['status_code'] == 201
            assert resultado['data']['rol'] == RolUsuario.ALUMNO

    # ==========================================
    # VALIDACIÓN DE CAMPOS FALTANTES (S3-S7)
    # ==========================================

    def test_registro_falta_nombre(self, app):
        """
        S3: Registro falla cuando falta campo 'nombre'.
        CASO ERROR: validación de campos obligatorios.
        """
        with app.app_context():
            datos = USUARIO_ADMIN_VALIDO.copy()
            del datos['nombre']
            
            resultado = AuthService.register_user(datos)
            
            assert resultado['success'] is False
            assert resultado['status_code'] == 400
            assert 'nombre' in resultado['error'].lower() or 'campo' in resultado['error'].lower()

    def test_registro_falta_correo(self, app):
        """
        S5: Registro falla cuando falta campo 'correo'.
        CASO ERROR: validación de campos obligatorios.
        """
        with app.app_context():
            datos = USUARIO_ADMIN_VALIDO.copy()
            del datos['correo']
            
            resultado = AuthService.register_user(datos)
            
            assert resultado['success'] is False
            assert resultado['status_code'] == 400

    def test_registro_falta_password(self, app):
        """
        S6: Registro falla cuando falta campo 'password'.
        CASO ERROR: validación de campos obligatorios.
        """
        with app.app_context():
            datos = USUARIO_ADMIN_VALIDO.copy()
            del datos['password']
            
            resultado = AuthService.register_user(datos)
            
            assert resultado['success'] is False
            assert resultado['status_code'] == 400

    def test_registro_falta_rol(self, app):
        """
        S7: Registro falla cuando falta campo 'rol'.
        CASO ERROR: validación de campos obligatorios.
        """
        with app.app_context():
            datos = USUARIO_ADMIN_VALIDO.copy()
            del datos['rol']
            
            resultado = AuthService.register_user(datos)
            
            assert resultado['success'] is False
            assert resultado['status_code'] == 400

    # ==========================================
    # VALIDACIÓN DE CORREO DUPLICADO (S8, CA-02)
    # ==========================================

    def test_registro_correo_duplicado(self, app, usuario_admin):
        """
        S8: Registro falla cuando el correo ya existe.
        CASO ERROR (CA-02): validación de duplicidad de correo.
        """
        with app.app_context():
            datos_duplicados = {
                "nombre": "Otro",
                "apellido": "Usuario",
                "correo": usuario_admin.correo,  # Ya registrado
                "password": "OtherPass123!",
                "rol": "DOCENTE"
            }
            
            resultado = AuthService.register_user(datos_duplicados)
            
            assert resultado['success'] is False
            assert resultado['status_code'] == 409
            assert 'correo' in resultado['error'].lower() or 'registrado' in resultado['error'].lower()

    # ==========================================
    # VALIDACIÓN DE ROL (S9)
    # ==========================================

    def test_registro_rol_invalido(self, app):
        """
        S9: Registro falla cuando el rol es inválido.
        CASO ERROR: validación de rol permitido.
        """
        with app.app_context():
            datos = USUARIO_ROL_INVALIDO.copy()
            
            resultado = AuthService.register_user(datos)
            
            assert resultado['success'] is False
            assert resultado['status_code'] == 400
            assert 'rol' in resultado['error'].lower()

    # ==========================================
    # CASOS LÍMITE (S10-S14)
    # ==========================================

    def test_registro_password_vacia(self, app):
        """
        S10: Registro con contraseña vacía.
        CASO LÍMITE: ¿debería rechazar o aceptar?
        """
        with app.app_context():
            datos = USUARIO_ADMIN_VALIDO.copy()
            datos['correo'] = "test.vacia@udl.edu.mx"
            datos['password'] = ""
            
            resultado = AuthService.register_user(datos)
            
            # Puede aceptar o rechazar, pero debe ser consistente
            if resultado['success']:
                # Si acepta, el usuario debe poder usarse
                assert resultado['status_code'] == 201
            else:
                # Si rechaza, debe tener código de error
                assert resultado['status_code'] in [400, 422]

    def test_registro_password_muy_corta(self, app):
        """
        S11: Registro con contraseña muy corta.
        CASO LÍMITE: ¿debería rechazar o aceptar?
        """
        with app.app_context():
            datos = USUARIO_ADMIN_VALIDO.copy()
            datos['correo'] = "test.corta@udl.edu.mx"
            datos['password'] = "123"
            
            resultado = AuthService.register_user(datos)
            
            # Puede aceptar o rechazar
            assert resultado['status_code'] in [201, 400, 422]

    def test_registro_usuario_inactivo_por_defecto(self, app):
        """
        S13: Usuario registrado debe estar activo por defecto.
        CASO NORMAL: campo activo=True.
        """
        with app.app_context():
            resultado = AuthService.register_user(USUARIO_ADMIN_VALIDO)
            
            assert resultado['success'] is True
            usuario = Usuario.query.filter_by(
                correo=USUARIO_ADMIN_VALIDO['correo']
            ).first()
            assert usuario.activo is True

    def test_registro_plantel_opcional(self, app):
        """
        S14: id_plantel_asignado es opcional.
        CASO LÍMITE: puede ser None.
        """
        with app.app_context():
            datos = USUARIO_ADMIN_VALIDO.copy()
            datos['correo'] = "test.sin.plantel@udl.edu.mx"
            # No incluir id_plantel_asignado
            if 'id_plantel_asignado' in datos:
                del datos['id_plantel_asignado']
            
            resultado = AuthService.register_user(datos)
            
            assert resultado['success'] is True
            usuario = Usuario.query.filter_by(
                correo=datos['correo']
            ).first()
            assert usuario.id_plantel_asignado is None

    # ==========================================
    # ENCRIPTACIÓN (S15)
    # ==========================================

    def test_registro_hashes_diferentes(self, app):
        """
        S15: Cada registro con misma contraseña genera hash diferente.
        CASO NORMAL: bcrypt usa salt aleatorio.
        """
        with app.app_context():
            datos1 = USUARIO_ADMIN_VALIDO.copy()
            datos1['correo'] = "test1.hash@udl.edu.mx"
            
            datos2 = USUARIO_DOCENTE_VALIDO.copy()
            datos2['correo'] = "test2.hash@udl.edu.mx"
            datos2['password'] = USUARIO_ADMIN_VALIDO['password']  # Misma contraseña
            
            resultado1 = AuthService.register_user(datos1)
            resultado2 = AuthService.register_user(datos2)
            
            assert resultado1['success'] is True
            assert resultado2['success'] is True
            
            usuario1 = Usuario.query.filter_by(correo=datos1['correo']).first()
            usuario2 = Usuario.query.filter_by(correo=datos2['correo']).first()
            
            # Los hashes deben ser diferentes
            assert usuario1.password_hash != usuario2.password_hash


@pytest.mark.unit
class TestAuthServiceLogin:
    """Pruebas unitarias para el login de usuarios."""

    # ==========================================
    # CASOS NORMALES (S16)
    # ==========================================

    def test_login_exitoso(self, app, usuario_admin):
        """
        S16: Login exitoso retorna token y datos del usuario.
        CASO NORMAL: credenciales correctas.
        """
        with app.app_context():
            resultado = AuthService.login(
                LOGIN_ADMIN_VALIDO['correo'],
                LOGIN_ADMIN_VALIDO['password']
            )
            
            assert resultado['success'] is True
            assert resultado['status_code'] == 200
            assert 'token' in resultado
            assert 'usuario' in resultado
            assert resultado['usuario']['correo'] == LOGIN_ADMIN_VALIDO['correo']

    def test_login_docente_exitoso(self, app, usuario_docente):
        """
        CASO NORMAL: Login exitoso para DOCENTE.
        """
        with app.app_context():
            resultado = AuthService.login(
                LOGIN_DOCENTE_VALIDO['correo'],
                LOGIN_DOCENTE_VALIDO['password']
            )
            
            assert resultado['success'] is True
            assert resultado['usuario']['rol'] == RolUsuario.DOCENTE

    # ==========================================
    # CASOS DE ERROR (S17-S19)
    # ==========================================

    def test_login_correo_inexistente(self, app):
        """
        S17: Login falla cuando el correo no existe.
        CASO ERROR: usuario no registrado.
        """
        with app.app_context():
            resultado = AuthService.login(
                "noexiste@udl.edu.mx",
                "AnyPassword123!"
            )
            
            assert resultado['success'] is False
            assert resultado['status_code'] == 401
            assert 'credenciales' in resultado['error'].lower()

    def test_login_password_incorrecta(self, app, usuario_admin):
        """
        S18: Login falla cuando la contraseña es incorrecta.
        CASO ERROR: contraseña no coincide.
        """
        with app.app_context():
            resultado = AuthService.login(
                LOGIN_ADMIN_VALIDO['correo'],
                "WrongPassword123!"
            )
            
            assert resultado['success'] is False
            assert resultado['status_code'] == 401

    def test_login_credenciales_vacias(self, app):
        """
        S19: Login falla con credenciales vacías.
        CASO ERROR: entrada vacía.
        """
        with app.app_context():
            resultado = AuthService.login("", "")
            
            assert resultado['success'] is False
            assert resultado['status_code'] == 401

    # ==========================================
    # VALIDACIÓN DE JWT (S21-S23)
    # ==========================================

    def test_login_token_contiene_rol(self, app, usuario_admin):
        """
        S21: Token JWT debe contener el rol del usuario.
        CASO NORMAL: payload completo.
        """
        with app.app_context():
            from app.utils.security import decode_token
            
            resultado = AuthService.login(
                LOGIN_ADMIN_VALIDO['correo'],
                LOGIN_ADMIN_VALIDO['password']
            )
            
            assert resultado['success'] is True
            payload = decode_token(resultado['token'])
            
            assert payload is not None
            assert payload['rol'] == RolUsuario.COORDINADOR

    def test_login_token_contiene_id_usuario(self, app, usuario_admin):
        """
        S22: Token JWT debe contener el id_usuario.
        CASO NORMAL: payload completo.
        """
        with app.app_context():
            from app.utils.security import decode_token
            
            resultado = AuthService.login(
                LOGIN_ADMIN_VALIDO['correo'],
                LOGIN_ADMIN_VALIDO['password']
            )
            
            assert resultado['success'] is True
            payload = decode_token(resultado['token'])
            
            assert payload is not None
            assert 'id_usuario' in payload
            assert payload['id_usuario'] == usuario_admin.id_usuario

    def test_login_token_contiene_exp(self, app, usuario_admin):
        """
        S23: Token JWT debe contener fecha de expiración.
        CASO NORMAL: exp presente en payload.
        """
        with app.app_context():
            from app.utils.security import decode_token
            from datetime import datetime
            
            resultado = AuthService.login(
                LOGIN_ADMIN_VALIDO['correo'],
                LOGIN_ADMIN_VALIDO['password']
            )
            
            assert resultado['success'] is True
            payload = decode_token(resultado['token'])
            
            assert payload is not None
            assert 'exp' in payload
            # exp debe ser un timestamp en el futuro
            assert payload['exp'] > datetime.utcnow().timestamp()
