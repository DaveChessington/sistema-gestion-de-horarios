"""
Test Blueprint para validar decoradores de autenticación y autorización.
Este blueprint NO debe ser usado en producción.
"""
from flask import Blueprint, jsonify
from app.utils.security import login_required, role_required


test_bp = Blueprint('test', __name__, url_prefix='/test')


@test_bp.route('/health', methods=['GET'])
def health():
    """Endpoint de prueba para verificar que el servidor está activo."""
    return jsonify({'status': 'ok'}), 200


@test_bp.route('/protected', methods=['GET'])
@login_required
def protected(current_user_payload):
    """Endpoint protegido para validar el decorador login_required."""
    return jsonify({'message': 'Protected route', 'user': current_user_payload}), 200


@test_bp.route('/admin-only', methods=['GET'])
@login_required
@role_required('COORDINADOR', 'ADMIN_PLANTEL')
def admin_only(current_user_payload):
    """Endpoint que requiere roles COORDINADOR o ADMIN_PLANTEL."""
    return jsonify({'message': 'Admin only route'}), 200


@test_bp.route('/docente-only', methods=['GET'])
@login_required
@role_required('DOCENTE')
def docente_only(current_user_payload):
    """Endpoint que requiere rol DOCENTE."""
    return jsonify({'message': 'Docente only route'}), 200
