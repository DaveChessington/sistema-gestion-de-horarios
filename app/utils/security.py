from functools import wraps
from flask import request, jsonify, current_app
import jwt
from datetime import datetime, timedelta

def generate_token(usuario):
    """Genera un JWT para el usuario especificado."""
    payload = {
        'id_usuario': usuario.id_usuario,
        'correo': usuario.correo,
        'rol': usuario.rol,
        'id_plantel_asignado': usuario.id_plantel_asignado,
        'exp': datetime.utcnow() + timedelta(hours=8)
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')

def decode_token(token):
    """Decodifica un JWT y retorna el payload o None si es inválido/expirado."""
    try:
        return jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None

def login_required(f):
    """Decorador para proteger rutas requiriendo un JWT válido."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Token faltante o formato inválido. Use Bearer <token>'}), 401
        
        token = token.split(" ")[1]
        payload = decode_token(token)
        
        if not payload:
            return jsonify({'error': 'Token inválido o expirado'}), 401
            
        # Inyectamos el payload en los kwargs para que el endpoint pueda usarlo
        kwargs['current_user_payload'] = payload
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    """Decorador para restringir el acceso a ciertos roles. Requiere ser usado DESPUÉS de @login_required."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            payload = kwargs.get('current_user_payload')
            if not payload:
                return jsonify({'error': 'Autenticación requerida para verificar roles'}), 401
                
            if payload.get('rol') not in roles:
                return jsonify({'error': 'No tienes permisos suficientes para acceder a este recurso'}), 403
                
            return f(*args, **kwargs)
        return decorated
    return decorator
