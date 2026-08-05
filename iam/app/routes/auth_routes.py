from flask import Blueprint, request, jsonify
from app.services.auth_service import AuthService
from app.utils.security import login_required, role_required

auth_bp = Blueprint('auth', __name__, url_prefix='/api/v1/auth')

@auth_bp.route('/register', methods=['POST'], strict_slashes=False)
def register():
    """Ruta para registrar nuevos usuarios."""
    datos = request.get_json()
    if not datos:
        return jsonify({'error': 'No se enviaron datos en la petición'}), 400
        
    resultado = AuthService.register_user(datos)
    if not resultado['success']:
        return jsonify({'error': resultado['error']}), resultado['status_code']
        
    return jsonify({'mensaje': 'Usuario registrado exitosamente', 'usuario': resultado['data']}), resultado['status_code']

@auth_bp.route('/login', methods=['POST'], strict_slashes=False)
def login():
    """Ruta para autenticar usuarios y obtener token."""
    datos = request.get_json()
    if not datos or 'correo' not in datos or 'password' not in datos:
        return jsonify({'error': 'Se requiere correo y password'}), 400
        
    resultado = AuthService.login(datos['correo'], datos['password'])
    if not resultado['success']:
        return jsonify({'error': resultado['error']}), resultado['status_code']
        
    return jsonify({
        'mensaje': 'Login exitoso', 
        'token': resultado['token'],
        'usuario': resultado['usuario']
    }), resultado['status_code']

@auth_bp.route('/me', methods=['GET'], strict_slashes=False)
@login_required
def get_me(current_user_payload):
    """Ruta protegida para obtener los datos del usuario logueado usando el token."""
    return jsonify({
        'mensaje': 'Token válido',
        'usuario': current_user_payload
    }), 200

# Ejemplo de ruta protegida por rol (solo para probar RBAC)
@auth_bp.route('/admin-solo', methods=['GET'], strict_slashes=False)
@login_required
@role_required('COORDINADOR', 'ADMIN_PLANTEL')
def admin_only(current_user_payload):
    """Ruta de prueba protegida por roles altos."""
    return jsonify({
        'mensaje': 'Tienes acceso a la zona de administración',
        'plantel': current_user_payload.get('id_plantel_asignado')
    }), 200
