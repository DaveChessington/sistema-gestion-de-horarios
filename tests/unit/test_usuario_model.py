"""
Pruebas unitarias del modelo Usuario.
Valida encriptación, métodos de verificación y exposición de datos.
"""
import pytest
from app.models.usuario import Usuario, RolUsuario


@pytest.mark.unit
class TestUsuarioModel:
    """Pruebas unitarias para el modelo Usuario."""

    # ==========================================
    # PRUEBAS DE ENCRIPTACIÓN (U1-U2)
    # ==========================================

    def test_set_password_genera_hash(self, app):
        """
        U1: Verificar que set_password() genera un hash de contraseña.
        CASO NORMAL: contraseña se encripta correctamente.
        """
        with app.app_context():
            usuario = Usuario(
                nombre="Test",
                apellido="User",
                correo="test@udl.edu.mx",
                rol=RolUsuario.DOCENTE
            )
            
            password = "SecurePass123!@"
            usuario.set_password(password)
            
            # El hash NO debe ser igual a la contraseña original
            assert usuario.password_hash != password
            # El hash debe existir
            assert usuario.password_hash is not None
            # El hash debe tener cierta longitud (bcrypt produce ~60 caracteres)
            assert len(usuario.password_hash) > 20

    def test_set_password_hash_diferente_cada_vez(self, app):
        """
        U2: Verificar que cada llamada a set_password() genera un hash diferente.
        CASO NORMAL: bcrypt con salt aleatorio produce hashes distintos.
        """
        with app.app_context():
            usuario1 = Usuario(
                nombre="Test1",
                apellido="User",
                correo="test1@udl.edu.mx",
                rol=RolUsuario.DOCENTE
            )
            usuario2 = Usuario(
                nombre="Test2",
                apellido="User",
                correo="test2@udl.edu.mx",
                rol=RolUsuario.DOCENTE
            )
            
            misma_password = "SamePassword123!"
            usuario1.set_password(misma_password)
            usuario2.set_password(misma_password)
            
            # Los hashes deben ser diferentes (debido al salt aleatorio de bcrypt)
            assert usuario1.password_hash != usuario2.password_hash

    # ==========================================
    # PRUEBAS DE VERIFICACIÓN (U3-U4)
    # ==========================================

    def test_check_password_correcto(self, app):
        """
        U3: Verificar que check_password() retorna True con contraseña correcta.
        CASO NORMAL: contraseña coincide con el hash.
        """
        with app.app_context():
            usuario = Usuario(
                nombre="Test",
                apellido="User",
                correo="test@udl.edu.mx",
                rol=RolUsuario.DOCENTE
            )
            
            password = "CorrectPass123!@"
            usuario.set_password(password)
            
            # Debe retornar True
            assert usuario.check_password(password) is True

    def test_check_password_incorrecto(self, app):
        """
        U4: Verificar que check_password() retorna False con contraseña incorrecta.
        CASO ERROR: contraseña no coincide.
        """
        with app.app_context():
            usuario = Usuario(
                nombre="Test",
                apellido="User",
                correo="test@udl.edu.mx",
                rol=RolUsuario.DOCENTE
            )
            
            password_correcta = "CorrectPass123!@"
            password_incorrecta = "WrongPass123!@"
            usuario.set_password(password_correcta)
            
            # Debe retornar False
            assert usuario.check_password(password_incorrecta) is False

    def test_check_password_vacia(self, app):
        """
        CASO LÍMITE: verificar contraseña vacía contra un hash.
        """
        with app.app_context():
            usuario = Usuario(
                nombre="Test",
                apellido="User",
                correo="test@udl.edu.mx",
                rol=RolUsuario.DOCENTE
            )
            
            usuario.set_password("RealPass123!")
            
            # Contraseña vacía debe retornar False
            assert usuario.check_password("") is False

    # ==========================================
    # PRUEBAS DE EXPOSICIÓN DE DATOS (U5)
    # ==========================================

    def test_to_dict_no_expone_password(self, app):
        """
        U5: Verificar que to_dict() NO incluye password_hash.
        CASO NORMAL: método to_dict() es seguro.
        """
        with app.app_context():
            usuario = Usuario(
                nombre="Test",
                apellido="User",
                correo="test@udl.edu.mx",
                rol=RolUsuario.DOCENTE
            )
            usuario.set_password("SecurePass123!")
            
            usuario_dict = usuario.to_dict()
            
            # El diccionario NO debe contener password_hash
            assert 'password_hash' not in usuario_dict
            # Pero sí debe contener otros campos
            assert 'id_usuario' in usuario_dict
            assert 'correo' in usuario_dict
            assert usuario_dict['nombre'] == "Test"

    def test_to_dict_contiene_rol(self, app):
        """
        CASO NORMAL: to_dict() incluye el rol del usuario.
        """
        with app.app_context():
            usuario = Usuario(
                nombre="Test",
                apellido="User",
                correo="test@udl.edu.mx",
                rol=RolUsuario.COORDINADOR
            )
            
            usuario_dict = usuario.to_dict()
            
            assert 'rol' in usuario_dict
            assert usuario_dict['rol'] == RolUsuario.COORDINADOR

    # ==========================================
    # PRUEBAS DE PRIORIDADES (U6-U9)
    # ==========================================

    def test_rol_coordinador_prioridad_4(self, app):
        """
        U6: COORDINADOR debe tener prioridad 4 (máxima).
        """
        with app.app_context():
            rol = RolUsuario.COORDINADOR
            assert rol.prioridad == 4

    def test_rol_admin_plantel_prioridad_3(self, app):
        """
        U7: ADMIN_PLANTEL debe tener prioridad 3.
        """
        with app.app_context():
            rol = RolUsuario.ADMIN_PLANTEL
            assert rol.prioridad == 3

    def test_rol_docente_prioridad_2(self, app):
        """
        U8: DOCENTE debe tener prioridad 2.
        """
        with app.app_context():
            rol = RolUsuario.DOCENTE
            assert rol.prioridad == 2

    def test_rol_alumno_prioridad_0(self, app):
        """
        U9: ALUMNO debe tener prioridad 0 (mínima).
        """
        with app.app_context():
            rol = RolUsuario.ALUMNO
            assert rol.prioridad == 0

    # ==========================================
    # PRUEBAS DE INICIALIZACIÓN (CASOS LÍMITE)
    # ==========================================

    def test_usuario_activo_por_defecto(self, app):
        """
        CASO NORMAL: usuario creado debe estar activo por defecto.
        """
        with app.app_context():
            usuario = Usuario(
                nombre="Test",
                apellido="User",
                correo="test@udl.edu.mx",
                rol=RolUsuario.ALUMNO
            )
            # Guardar en BD para aplicar el default
            from app.extensions import db
            db.session.add(usuario)
            db.session.commit()
            
            # Por defecto debe estar activo
            assert usuario.activo is True

    def test_usuario_inactivo_puede_crearse(self, app):
        """
        CASO LÍMITE: permitir crear usuario inactivo.
        """
        with app.app_context():
            usuario = Usuario(
                nombre="Test",
                apellido="User",
                correo="test@udl.edu.mx",
                rol=RolUsuario.ALUMNO,
                activo=False
            )
            
            assert usuario.activo is False

    def test_usuario_con_plantel_asignado(self, app):
        """
        CASO NORMAL: usuario puede tener plantel asignado.
        """
        with app.app_context():
            usuario = Usuario(
                nombre="Test",
                apellido="User",
                correo="test@udl.edu.mx",
                rol=RolUsuario.DOCENTE,
                id_plantel_asignado=5
            )
            
            assert usuario.id_plantel_asignado == 5

    def test_usuario_sin_plantel_asignado(self, app):
        """
        CASO LÍMITE: usuario sin plantel asignado (None).
        """
        with app.app_context():
            usuario = Usuario(
                nombre="Test",
                apellido="User",
                correo="test@udl.edu.mx",
                rol=RolUsuario.ALUMNO
            )
            
            assert usuario.id_plantel_asignado is None
