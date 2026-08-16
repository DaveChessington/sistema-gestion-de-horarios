from functools import wraps
from flask import request, jsonify, current_app
import jwt


def decode_token(token):
    """Decodifica un JWT y retorna el payload o None si es inválido o ha expirado."""
    try:
        return jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def login_required(f):
    """Decorador para proteger endpoints exigiendo un token JWT válido."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Token de autenticación faltante o formato inválido. Use Bearer <token>'}), 401
        
        token = auth_header.split(" ")[1]
        payload = decode_token(token)
        
        if not payload:
            return jsonify({'error': 'Token inválido o expirado'}), 401
            
        kwargs['current_user_payload'] = payload
        return f(*args, **kwargs)
    return decorated


def get_user_role_weight(rol: str) -> int:
    """
    Retorna el peso del rol de usuario (U) según las especificaciones del sistema:
    - COORDINADOR / DOCENTE: 40
    - ADMIN_PLANTEL / ENCARGADO: 30
    - ALUMNO: 10
    """
    if not rol:
        return 10
    
    rol_upper = str(rol).upper()
    pesos = {
        'COORDINADOR': 40,
        'DOCENTE': 40,
        'PROFESOR': 40,
        'MAESTRO': 40,
        'ADMIN_PLANTEL': 30,
        'ENCARGADO': 30,
        'ADMINISTRADOR': 30,
        'ALUMNO': 10,
        'ESTUDIANTE': 10
    }
    return pesos.get(rol_upper, 10)


def get_event_type_weight(id_tipo_evento: int) -> int:
    """
    Retorna el peso del tipo de evento (E) en caso de fallback:
    - Clase Curricular (1): 50
    - Evento Institucional (2): 40
    - Conferencia / Taller (3): 30
    - Sesión de Estudio (4): 10
    """
    pesos = {
        1: 50,
        2: 40,
        3: 30,
        4: 10
    }
    return pesos.get(id_tipo_evento, 10)
