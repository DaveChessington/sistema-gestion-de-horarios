import os
from functools import wraps
from flask import request, jsonify, current_app, g
import jwt


class AuthError(Exception):
    pass


def get_jwt_secret_key():
    return os.environ.get('JWT_SECRET_KEY') or current_app.config.get('JWT_SECRET_KEY') or current_app.config.get('SECRET_KEY')


def decode_token(token):
    try:
        return jwt.decode(token, get_jwt_secret_key(), algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        raise AuthError('Token expirado')
    except jwt.InvalidTokenError:
        raise AuthError('Token inválido')


def get_current_user():
    auth_header = request.headers.get('Authorization', '')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise AuthError('Token faltante o formato inválido. Use Authorization: Bearer <token>')

    token = auth_header.split(' ', 1)[1].strip()
    if not token:
        raise AuthError('Token faltante o formato inválido. Use Authorization: Bearer <token>')

    payload = decode_token(token)
    current_user = {
        'id_usuario': payload.get('id_usuario'),
        'email': payload.get('correo'),
        'rol': payload.get('rol'),
        # Prefer 'id_plantel_asignado' but fallback to 'id_plantel' if not present
        'id_plantel': payload.get('id_plantel_asignado') or payload.get('id_plantel')
    }

    if not current_user['id_usuario'] or not current_user['rol']:
        raise AuthError('Token válido pero payload incompleto')

    return current_user


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            current_user = get_current_user()
        except AuthError as error:
            return jsonify({'error': str(error)}), 401

        g.current_user = current_user
        return f(*args, **kwargs)

    return decorated


def require_roles(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            current_user = getattr(g, 'current_user', None)
            if not current_user:
                return jsonify({'error': 'Autenticación requerida'}), 401

            if current_user.get('rol') not in roles:
                return jsonify({'error': 'No tienes permisos suficientes para acceder a este recurso'}), 403

            return f(*args, **kwargs)

        return decorated
    return decorator
