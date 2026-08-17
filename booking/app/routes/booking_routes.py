from flask import Blueprint, request, jsonify
from booking.app.utils.security import login_required
from booking.app.services.booking_service import (
    create_booking_request,
    get_booking_history,
    get_booking_request,
    update_booking_request,
    cancel_booking_request
)

booking_bp = Blueprint('booking', __name__)


@booking_bp.route('/booking/request', methods=['POST'])
@login_required
def request_booking(current_user_payload):
    """
    Endpoint POST /api/v1/booking/request
    Registra una solicitud de reserva de espacio, ejecutando la lógica de colisión y prioridad.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Payload JSON no proporcionado'}), 400

    # Validar que venga fecha o fecha_reserva
    fecha_presente = 'fecha_reserva' in data or 'fecha' in data
    campos_requeridos = ['id_salon', 'hora_inicio', 'hora_fin', 'id_tipo_evento']
    faltantes = [campo for campo in campos_requeridos if campo not in data or data[campo] is None]
    
    if not fecha_presente:
        faltantes.append('fecha_reserva (o fecha)')

    if faltantes:
        return jsonify({'error': f'Campos requeridos faltantes: {", ".join(faltantes)}'}), 400

    response, status_code = create_booking_request(data, current_user_payload)
    return jsonify(response), status_code


@booking_bp.route('/booking/history', methods=['GET'])
@login_required
def booking_history(current_user_payload):
    """
    Endpoint GET /api/v1/booking/history
    Retorna el historial de peticiones de reservas realizadas por el usuario o filtradas por rol.
    Query params opcionales: estado, id_salon, fecha, fecha_reserva, id_usuario
    """
    filters = {
        'estado': request.args.get('estado'),
        'id_salon': request.args.get('id_salon'),
        'fecha': request.args.get('fecha'),
        'fecha_reserva': request.args.get('fecha_reserva'),
        'id_usuario': request.args.get('id_usuario')
    }
    
    # Limpiar filtros nulos
    filters = {k: v for k, v in filters.items() if v is not None}

    response, status_code = get_booking_history(current_user_payload, filters)
    return jsonify(response), status_code


@booking_bp.route('/booking/request/<int:id_peticion>', methods=['DELETE'])
@login_required
def cancel_booking(current_user_payload, id_peticion):
    """
    Endpoint DELETE /api/v1/booking/request/<int:id_peticion>
    Cancela una reserva existente y libera el espacio en la base de datos.
    """
    response, status_code = cancel_booking_request(id_peticion, current_user_payload)
    return jsonify(response), status_code


@booking_bp.route('/booking/request/<int:id_peticion>', methods=['GET'])
@login_required
def booking_request_detail(current_user_payload, id_peticion):
    """Consulta una petición respetando propiedad y alcance administrativo."""
    response, status_code = get_booking_request(id_peticion, current_user_payload)
    return jsonify(response), status_code


@booking_bp.route('/booking/request/<int:id_peticion>', methods=['PATCH', 'PUT'])
@login_required
def update_booking(current_user_payload, id_peticion):
    """Actualiza o reprograma una reserva sin omitir colisiones ni prioridad."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Payload JSON no proporcionado'}), 400
    response, status_code = update_booking_request(
        id_peticion,
        data,
        current_user_payload,
    )
    return jsonify(response), status_code
