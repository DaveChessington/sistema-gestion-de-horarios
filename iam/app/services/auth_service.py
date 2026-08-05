from app.extensions import db
from app.models.usuario import Usuario
from app.utils.security import generate_token

class AuthService:
    
    @staticmethod
    def register_user(datos):
        """Registra un nuevo usuario aplicando las reglas de negocio."""
        required_fields = ['nombre', 'apellido', 'correo', 'password', 'rol']
        for field in required_fields:
            if field not in datos:
                return {'success': False, 'error': f'Falta el campo obligatorio: {field}', 'status_code': 400}
        
        # Validar si el correo ya existe
        if Usuario.query.filter_by(correo=datos['correo']).first():
            return {'success': False, 'error': 'El correo ya está registrado', 'status_code': 409}
            
        # Validar rol
        roles_permitidos = ['COORDINADOR', 'ADMIN_PLANTEL', 'DOCENTE', 'ALUMNO']
        if datos['rol'] not in roles_permitidos:
            return {'success': False, 'error': 'Rol inválido', 'status_code': 400}
            
        # Crear usuario
        nuevo_usuario = Usuario(
            nombre=datos['nombre'],
            apellido=datos['apellido'],
            correo=datos['correo'],
            rol=datos['rol'],
            id_plantel_asignado=datos.get('id_plantel_asignado')
        )
        # RF-01: Cifrado de Credenciales
        nuevo_usuario.set_password(datos['password'])
        
        try:
            db.session.add(nuevo_usuario)
            db.session.commit()
            return {'success': True, 'data': nuevo_usuario.to_dict(), 'status_code': 201}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': 'Error interno al guardar en la base de datos', 'status_code': 500}

    @staticmethod
    def login(correo, password):
        """Verifica credenciales y retorna un token en caso de éxito."""
        usuario = Usuario.query.filter_by(correo=correo).first()
        
        # Validar existencia de usuario y contraseña
        if not usuario or not usuario.check_password(password):
            return {'success': False, 'error': 'Credenciales inválidas', 'status_code': 401}
            
        # Validar que el usuario esté activo
        if not usuario.activo:
            return {'success': False, 'error': 'Cuenta de usuario inactiva', 'status_code': 403}
            
        # Generar token
        token = generate_token(usuario)
        return {
            'success': True, 
            'token': token, 
            'usuario': usuario.to_dict(), 
            'status_code': 200
        }
