from app.extensions import db
from app.models.usuario import Usuario, RolUsuario


class AuthService:
    @staticmethod
    def register_user(data):
        required_fields = ['nombre', 'correo', 'password', 'rol']
        for field in required_fields:
            if field not in data or data[field] in [None, '']:
                return {
                    'success': False,
                    'status_code': 400,
                    'error': f'Campo {field} es obligatorio'
                }

        existing_user = Usuario.query.filter_by(correo=data['correo']).first()
        if existing_user is not None:
            return {
                'success': False,
                'status_code': 409,
                'error': 'Correo ya registrado'
            }

        if data['rol'] not in {rol.value for rol in RolUsuario}:
            return {
                'success': False,
                'status_code': 400,
                'error': 'Rol inválido'
            }

        usuario = Usuario(
            nombre=data['nombre'],
            apellido=data.get('apellido', ''),
            correo=data['correo'],
            rol=RolUsuario(data['rol']),
            activo=True,
            id_plantel_asignado=data.get('id_plantel_asignado')
        )
        usuario.set_password(data['password'])
        db.session.add(usuario)
        db.session.commit()

        return {
            'success': True,
            'status_code': 201,
            'data': usuario.to_dict()
        }

    @staticmethod
    def login(correo, password):
        if not correo or not password:
            return {
                'success': False,
                'status_code': 401,
                'error': 'Credenciales inválidas'
            }

        usuario = Usuario.query.filter_by(correo=correo).first()
        if not usuario or not usuario.check_password(password):
            return {
                'success': False,
                'status_code': 401,
                'error': 'Credenciales inválidas'
            }

        if not usuario.activo:
            return {
                'success': False,
                'status_code': 401,
                'error': 'Usuario inactivo'
            }

        from app.utils.security import generate_token

        return {
            'success': True,
            'status_code': 200,
            'token': generate_token(usuario),
            'usuario': usuario.to_dict()
        }
