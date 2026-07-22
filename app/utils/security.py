from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import current_app, jsonify, request
import jwt


def _get_user_value(usuario, attribute):
    try:
        value = getattr(usuario, attribute, None)
    except Exception:
        value = None

    if value is None:
        if hasattr(usuario, '__dict__'):
            value = usuario.__dict__.get(attribute)

    if hasattr(value, 'value'):
        return value.value
    return value


def generate_token(usuario):
    payload = {
        'id_usuario': _get_user_value(usuario, 'id_usuario'),
        'correo': _get_user_value(usuario, 'correo'),
        'rol': _get_user_value(usuario, 'rol'),
        'id_plantel_asignado': _get_user_value(usuario, 'id_plantel_asignado'),
        'exp': int((datetime.now(timezone.utc) + timedelta(hours=8)).timestamp())
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')


def decode_token(token):
    if not token:
        return None
    try:
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        if 'exp' not in payload:
            return None
        return payload
    except Exception:
        return None


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Token requerido'}), 401

        token = auth_header.split(' ', 1)[1]
        payload = decode_token(token)
        if not payload:
            return jsonify({'error': 'Token inválido'}), 401

        request.current_user_payload = payload
        kwargs['current_user_payload'] = payload
        return fn(*args, **kwargs)

    return wrapper


def role_required(*allowed_roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            payload = kwargs.get('current_user_payload', None)
            if payload is None:
                payload = getattr(request, 'current_user_payload', None)
            if not payload:
                return jsonify({'error': 'Autenticación requerida'}), 401

            role = payload.get('rol')
            if isinstance(role, str):
                role_value = role
            else:
                role_value = getattr(role, 'value', role)

            if role_value not in allowed_roles:
                return jsonify({'error': 'Permisos insuficientes'}), 403

            return fn(*args, **kwargs)

        return wrapper

    return decorator
