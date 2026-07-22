from flask import Blueprint, jsonify
from app.utils.security import login_required, role_required


auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'}), 200


@auth_bp.route('/protected', methods=['GET'])
@login_required
def protected(current_user_payload):
    return jsonify({'message': 'Protected route', 'user': current_user_payload}), 200


@auth_bp.route('/admin-only', methods=['GET'])
@login_required
@role_required('COORDINADOR', 'ADMIN_PLANTEL')
def admin_only(current_user_payload):
    return jsonify({'message': 'Admin only route'}), 200


@auth_bp.route('/docente-only', methods=['GET'])
@login_required
@role_required('DOCENTE')
def docente_only(current_user_payload):
    return jsonify({'message': 'Docente only route'}), 200
