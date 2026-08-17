from flask import Blueprint, request, jsonify
from booking.app.services.booking_service import get_schedule_grid

schedule_bp = Blueprint('schedule', __name__)


@schedule_bp.route('/schedule/grid', methods=['GET'])
def schedule_grid():
    """
    Endpoint GET /api/v1/schedule/grid
    Retorna la cuadrícula/matriz de horarios ocupados en formato JSON.
    Query params opcionales: id_plantel, id_salon, id_programa, fecha, fecha_reserva
    """
    filters = {
        'id_plantel': request.args.get('id_plantel'),
        'id_salon': request.args.get('id_salon'),
        'id_programa': request.args.get('id_programa'),
        'fecha': request.args.get('fecha'),
        'fecha_reserva': request.args.get('fecha_reserva')
    }
    filters = {k: v for k, v in filters.items() if v is not None}

    response, status_code = get_schedule_grid(filters)
    return jsonify(response), status_code
