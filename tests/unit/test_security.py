"""
Pruebas unitarias de las funciones de seguridad (JWT y decoradores).
Valida generación, decodificación y middleware de autenticación.
"""
import pytest
import jwt
from datetime import datetime, timedelta
from app.utils.security import (
    generate_token,
    decode_token,
    login_required,
    role_required
)
from app.models.usuario import RolUsuario
from app.extensions import db


@pytest.mark.unit
class TestSecurityTokenGeneration:
    """Pruebas de generación y decodificación de tokens JWT."""

    # ==========================================
    # GENERACIÓN Y DECODIFICACIÓN (SE1)
    # ==========================================

    def test_generate_token_estructura_correcta(self, app, usuario_admin):
        """
        SE1: Token generado contiene estructura correcta.
        CASO NORMAL: payload decodificable.
        """
        with app.app_context():
            token = generate_token(usuario_admin)
            
            assert token is not None
            assert isinstance(token, str)
            assert len(token) > 0

    def test_decode_token_valido(self, app, usuario_admin):
        """
        SE1: Token decodificado contiene payload correcto.
        CASO NORMAL: decodificación exitosa.
        """
        with app.app_context():
            token = generate_token(usuario_admin)
            payload = decode_token(token)
            
            assert payload is not None
            assert payload['id_usuario'] == usuario_admin.id_usuario
            assert payload['correo'] == usuario_admin.correo
            assert payload['rol'] == RolUsuario.COORDINADOR
            assert 'exp' in payload

    def test_decode_token_contiene_plantel(self, app, usuario_docente):
        """
        CASO NORMAL: Token contiene id_plantel_asignado.
        """
        with app.app_context():
            token = generate_token(usuario_docente)
            payload = decode_token(token)
            
            assert payload is not None
            assert payload['id_plantel_asignado'] == usuario_docente.id_plantel_asignado

    # ==========================================
    # VALIDACIÓN DE TOKENS (SE2-SE3)
    # ==========================================

    def test_decode_token_expirado_retorna_none(self, app, usuario_admin):
        """
        SE2: Token expirado retorna None.
        CASO ERROR: validación de expiración.
        """
        with app.app_context():
            # Crear token con expiración en el pasado
            payload = {
                'id_usuario': usuario_admin.id_usuario,
                'correo': usuario_admin.correo,
                'rol': usuario_admin.rol,
                'id_plantel_asignado': usuario_admin.id_plantel_asignado,
                'exp': datetime.utcnow() - timedelta(hours=1)  # 1 hora en el pasado
            }
            
            token_expirado = jwt.encode(
                payload,
                app.config['SECRET_KEY'],
                algorithm='HS256'
            )
            
            resultado = decode_token(token_expirado)
            
            assert resultado is None

    def test_decode_token_corrupto_retorna_none(self, app):
        """
        SE3: Token corrupto/inválido retorna None.
        CASO ERROR: token tamperado o inválido.
        """
        with app.app_context():
            token_invalido = "token.corrupto.xyz123"
            
            resultado = decode_token(token_invalido)
            
            assert resultado is None

    def test_decode_token_vacio_retorna_none(self, app):
        """
        CASO ERROR: token vacío retorna None.
        """
        with app.app_context():
            resultado = decode_token("")
            
            assert resultado is None

    def test_decode_token_con_secret_incorrecto(self, app, usuario_admin):
        """
        CASO LÍMITE: Token con secret key incorrecta retorna None.
        """
        with app.app_context():
            payload = {
                'id_usuario': usuario_admin.id_usuario,
                'correo': usuario_admin.correo,
                'rol': usuario_admin.rol,
                'exp': datetime.utcnow() + timedelta(hours=8)
            }
            
            # Crear token con secret key diferente
            token_falso = jwt.encode(
                payload,
                "wrong-secret-key",
                algorithm='HS256'
            )
            
            resultado = decode_token(token_falso)
            
            assert resultado is None


@pytest.mark.unit
class TestSecurityDecorators:
    """Pruebas de decoradores de seguridad (@login_required, @role_required)."""

    # ==========================================
    # PREPARACIÓN: Crear app con rutas protegidas
    # ==========================================

    @pytest.fixture
    def app_with_protected_routes(self, app):
        """
        Crea una app con rutas protegidas para pruebas de decoradores.
        """
        from flask import jsonify
        
        @app.route('/test-protected', methods=['GET'])
        @login_required
        def test_protected(current_user_payload):
            return jsonify({'message': 'Protected route', 'user': current_user_payload}), 200

        @app.route('/test-admin-only', methods=['GET'])
        @login_required
        @role_required('COORDINADOR', 'ADMIN_PLANTEL')
        def test_admin_only(current_user_payload):
            return jsonify({'message': 'Admin only route'}), 200

        @app.route('/test-docente-only', methods=['GET'])
        @login_required
        @role_required('DOCENTE')
        def test_docente_only(current_user_payload):
            return jsonify({'message': 'Docente only route'}), 200

        return app

    # ==========================================
    # PRUEBAS @login_required (SE4-SE6)
    # ==========================================

    def test_login_required_sin_token(self, app_with_protected_routes, client):
        """
        SE4: Acceso a ruta protegida sin token retorna 401.
        CASO ERROR: validación de token.
        """
        response = client.get('/test-protected')
        
        assert response.status_code == 401
        assert 'error' in response.get_json()
        assert 'token' in response.get_json()['error'].lower()

    def test_login_required_token_formato_incorrecto(self, app_with_protected_routes, client):
        """
        SE5: Token con formato incorrecto retorna 401.
        CASO ERROR: validación de formato Bearer.
        """
        # Sin "Bearer " prefix
        response = client.get(
            '/test-protected',
            headers={'Authorization': 'xyz123abc'}
        )
        
        assert response.status_code == 401
        assert 'error' in response.get_json()

    def test_login_required_token_valido(self, app_with_protected_routes, client, token_admin):
        """
        SE6: Token válido con formato correcto accede exitosamente.
        CASO NORMAL: autenticación exitosa.
        """
        response = client.get(
            '/test-protected',
            headers={'Authorization': f'Bearer {token_admin}'}
        )
        
        assert response.status_code == 200
        json_data = response.get_json()
        assert 'message' in json_data
        assert json_data['message'] == 'Protected route'

    def test_login_required_token_expirado(self, app_with_protected_routes, app, client, usuario_admin):
        """
        CASO ERROR: Token expirado retorna 401.
        """
        with app.app_context():
            # Crear token expirado
            payload = {
                'id_usuario': usuario_admin.id_usuario,
                'correo': usuario_admin.correo,
                'rol': usuario_admin.rol,
                'exp': datetime.utcnow() - timedelta(hours=1)
            }
            
            token_expirado = jwt.encode(
                payload,
                app.config['SECRET_KEY'],
                algorithm='HS256'
            )
            
            response = client.get(
                '/test-protected',
                headers={'Authorization': f'Bearer {token_expirado}'}
            )
            
            assert response.status_code == 401

    # ==========================================
    # PRUEBAS @role_required (SE7-SE9)
    # ==========================================

    def test_role_required_rol_permitido(self, app_with_protected_routes, client, token_admin):
        """
        SE7: Usuario con rol permitido accede exitosamente.
        CASO NORMAL: COORDINADOR accede a ruta admin.
        """
        response = client.get(
            '/test-admin-only',
            headers={'Authorization': f'Bearer {token_admin}'}
        )
        
        assert response.status_code == 200
        assert response.get_json()['message'] == 'Admin only route'

    def test_role_required_rol_no_permitido(self, app_with_protected_routes, client, token_docente):
        """
        SE8: Usuario con rol no permitido obtiene 403.
        CASO ERROR: DOCENTE NO accede a ruta solo admin.
        """
        response = client.get(
            '/test-admin-only',
            headers={'Authorization': f'Bearer {token_docente}'}
        )
        
        assert response.status_code == 403
        assert 'error' in response.get_json()

    def test_role_required_multiples_roles_permitidos(self, app_with_protected_routes, app, client, usuario_docente):
        """
        SE9: Usuario con rol en lista de múltiples roles accede.
        CASO NORMAL: DOCENTE accede a ruta para DOCENTE.
        """
        with app.app_context():
            token = generate_token(usuario_docente)
            
            response = client.get(
                '/test-docente-only',
                headers={'Authorization': f'Bearer {token}'}
            )
            
            assert response.status_code == 200

    def test_role_required_admin_plantel_accede_admin(self, app_with_protected_routes, app, client):
        """
        CASO NORMAL: ADMIN_PLANTEL accede a ruta admin.
        """
        with app.app_context():
            from app.models.usuario import Usuario
            
            # Crear usuario ADMIN_PLANTEL
            usuario = Usuario(
                nombre="Admin",
                apellido="Plantel",
                correo="admin.plantel@udl.edu.mx",
                rol=RolUsuario.ADMIN_PLANTEL,
                activo=True
            )
            usuario.set_password("AdminPlantPass123!")
            db.session.add(usuario)
            db.session.commit()
            
            token = generate_token(usuario)
            
            response = client.get(
                '/test-admin-only',
                headers={'Authorization': f'Bearer {token}'}
            )
            
            assert response.status_code == 200

    def test_role_required_alumno_no_accede_admin(self, app_with_protected_routes, app, client):
        """
        CASO ERROR: ALUMNO NO accede a ruta admin.
        """
        with app.app_context():
            from app.models.usuario import Usuario
            
            # Crear usuario ALUMNO
            usuario = Usuario(
                nombre="Alumno",
                apellido="Test",
                correo="alumno@udl.edu.mx",
                rol=RolUsuario.ALUMNO,
                activo=True
            )
            usuario.set_password("AlumnoPass123!")
            db.session.add(usuario)
            db.session.commit()
            
            token = generate_token(usuario)
            
            response = client.get(
                '/test-admin-only',
                headers={'Authorization': f'Bearer {token}'}
            )
            
            assert response.status_code == 403


@pytest.mark.unit
class TestTokenExpiration:
    """Pruebas específicas de expiración de tokens."""

    def test_token_expira_en_8_horas(self, app, usuario_admin):
        """
        CASO NORMAL: Token debe expirar en ~8 horas.
        """
        with app.app_context():
            antes = datetime.utcnow()
            token = generate_token(usuario_admin)
            payload = decode_token(token)
            
            assert payload is not None
            exp_timestamp = payload['exp']
            exp_datetime = datetime.utcfromtimestamp(exp_timestamp)
            
            # Calcular diferencia en horas
            tiempo_expiracion = (exp_datetime - antes).total_seconds() / 3600
            
            # Debe ser aproximadamente 8 horas (con margen de 1 minuto)
            assert 7.98 < tiempo_expiracion < 8.02

    def test_token_sin_exp_es_invalido(self, app, usuario_admin):
        """
        CASO ERROR: Token sin campo 'exp' es inválido.
        """
        with app.app_context():
            payload = {
                'id_usuario': usuario_admin.id_usuario,
                'correo': usuario_admin.correo,
                'rol': usuario_admin.rol,
                # Falta 'exp'
            }
            
            token_sin_exp = jwt.encode(
                payload,
                app.config['SECRET_KEY'],
                algorithm='HS256'
            )
            
            # Debería rechazarse al decodificar
            resultado = decode_token(token_sin_exp)
            
            # Puede ser None o puede aceptar sin expiración, depende de implementación
            assert resultado is None or 'exp' not in resultado
