from flask import Blueprint, request, jsonify
from app.services.catalog_service import (
    CampusService,
    EquipmentService,
    ProgramService,
    EntityNotFoundException,
    DuplicateEntityException,
    InvalidDataException
)

# Definir el Blueprint para el Catálogo
catalog_bp = Blueprint('catalog', __name__)


# --- ENDPOINTS PLANTEL ---

@catalog_bp.route('/planteles', methods=['POST'])
def create_plantel():
    data = request.get_json() or {}
    try:
        plantel = CampusService.create_plantel(
            nombre=data.get('nombre'),
            direccion=data.get('direccion')
        )
        return jsonify(plantel.to_dict()), 201
    except InvalidDataException as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Error interno del servidor.'}), 500

@catalog_bp.route('/planteles', methods=['GET'])
def list_planteles():
    # Permitir listar inactivos opcionalmente (sólo para admin)
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    planteles = CampusService.list_planteles(active_only=active_only)
    return jsonify([p.to_dict() for p in planteles]), 200

@catalog_bp.route('/planteles/<int:id_plantel>', methods=['GET'])
def get_plantel(id_plantel):
    try:
        plantel = CampusService.get_plantel_by_id(id_plantel, active_only=True)
        return jsonify(plantel.to_dict()), 200
    except EntityNotFoundException as e:
        return jsonify({'error': str(e)}), 404

@catalog_bp.route('/planteles/<int:id_plantel>', methods=['PUT'])
def update_plantel(id_plantel):
    data = request.get_json() or {}
    try:
        plantel = CampusService.update_plantel(
            plantel_id=id_plantel,
            nombre=data.get('nombre'),
            direccion=data.get('direccion')
        )
        return jsonify(plantel.to_dict()), 200
    except EntityNotFoundException as e:
        return jsonify({'error': str(e)}), 404
    except InvalidDataException as e:
        return jsonify({'error': str(e)}), 400

@catalog_bp.route('/planteles/<int:id_plantel>', methods=['DELETE'])
def delete_plantel(id_plantel):
    try:
        res = CampusService.delete_plantel(id_plantel)
        return jsonify(res), 200
    except EntityNotFoundException as e:
        return jsonify({'error': str(e)}), 404


# --- ENDPOINTS SALON ---

@catalog_bp.route('/salones', methods=['POST'])
def create_salon():
    data = request.get_json() or {}
    try:
        salon = CampusService.create_salon(
            numero=data.get('numero'),
            descripcion=data.get('descripcion'),
            capacidad=data.get('capacidad'),
            id_plantel=data.get('id_plantel')
        )
        return jsonify(salon.to_dict()), 201
    except InvalidDataException as e:
        return jsonify({'error': str(e)}), 400
    except EntityNotFoundException as e:
        return jsonify({'error': f"Error de relación: {str(e)}"}), 400
    except Exception as e:
        return jsonify({'error': 'Error interno del servidor.'}), 500

@catalog_bp.route('/salones', methods=['GET'])
def list_salones():
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    id_plantel = request.args.get('id_plantel', type=int)
    software_id = request.args.get('software_id', type=int)
    
    salones = CampusService.list_salones(
        active_only=active_only,
        id_plantel=id_plantel,
        software_id=software_id
    )
    return jsonify([s.to_dict() for s in salones]), 200

@catalog_bp.route('/salones/<int:id_salon>', methods=['GET'])
def get_salon(id_salon):
    try:
        salon = CampusService.get_salon_by_id(id_salon, active_only=True)
        return jsonify(salon.to_dict()), 200
    except EntityNotFoundException as e:
        return jsonify({'error': str(e)}), 404

@catalog_bp.route('/salones/<int:id_salon>', methods=['PUT'])
def update_salon(id_salon):
    data = request.get_json() or {}
    try:
        salon = CampusService.update_salon(
            id_salon=id_salon,
            numero=data.get('numero'),
            descripcion=data.get('descripcion'),
            capacidad=data.get('capacidad'),
            id_plantel=data.get('id_plantel')
        )
        return jsonify(salon.to_dict()), 200
    except EntityNotFoundException as e:
        return jsonify({'error': str(e)}), 404
    except InvalidDataException as e:
        return jsonify({'error': str(e)}), 400

@catalog_bp.route('/salones/<int:id_salon>', methods=['DELETE'])
def delete_salon(id_salon):
    try:
        res = CampusService.delete_salon(id_salon)
        return jsonify(res), 200
    except EntityNotFoundException as e:
        return jsonify({'error': str(e)}), 404


# --- ENDPOINTS EQUIPO (HARDWARE) ---

@catalog_bp.route('/equipos', methods=['POST'])
def create_equipment():
    data = request.get_json() or {}
    try:
        equipo = EquipmentService.create_equipment(
            numero=data.get('numero'),
            descripcion=data.get('descripcion'),
            id_salon=data.get('id_salon')
        )
        return jsonify(equipo.to_dict()), 201
    except DuplicateEntityException as e:
        return jsonify({'error': str(e)}), 409
    except (InvalidDataException, EntityNotFoundException) as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Error interno del servidor.'}), 500

@catalog_bp.route('/equipos', methods=['GET'])
def list_equipments():
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    id_salon = request.args.get('id_salon', type=int)
    
    equipos = EquipmentService.list_equipments(
        active_only=active_only,
        id_salon=id_salon
    )
    return jsonify([e.to_dict() for e in equipos]), 200

@catalog_bp.route('/equipos/<int:id_equipo>', methods=['GET'])
def get_equipment(id_equipo):
    try:
        equipo = EquipmentService.get_equipment_by_id(id_equipo, active_only=True)
        return jsonify(equipo.to_dict()), 200
    except EntityNotFoundException as e:
        return jsonify({'error': str(e)}), 404

@catalog_bp.route('/equipos/<int:id_equipo>', methods=['PUT'])
def update_equipment(id_equipo):
    data = request.get_json() or {}
    try:
        equipo = EquipmentService.update_equipment(
            id_equipo=id_equipo,
            numero=data.get('numero'),
            descripcion=data.get('descripcion'),
            id_salon=data.get('id_salon')
        )
        return jsonify(equipo.to_dict()), 200
    except EntityNotFoundException as e:
        return jsonify({'error': str(e)}), 404
    except DuplicateEntityException as e:
        return jsonify({'error': str(e)}), 409
    except InvalidDataException as e:
        return jsonify({'error': str(e)}), 400

@catalog_bp.route('/equipos/<int:id_equipo>', methods=['DELETE'])
def delete_equipment(id_equipo):
    try:
        res = EquipmentService.delete_equipment(id_equipo)
        return jsonify(res), 200
    except EntityNotFoundException as e:
        return jsonify({'error': str(e)}), 404


# --- ENDPOINTS SOFTWARE / PROGRAMAS ---

@catalog_bp.route('/programas', methods=['POST'])
def create_program():
    data = request.get_json() or {}
    try:
        programa = ProgramService.create_program(
            nombre=data.get('nombre'),
            descripcion=data.get('descripcion')
        )
        return jsonify(programa.to_dict()), 201
    except InvalidDataException as e:
        return jsonify({'error': str(e)}), 400

@catalog_bp.route('/programas', methods=['GET'])
def list_programs():
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    programas = ProgramService.list_programs(active_only=active_only)
    return jsonify([p.to_dict() for p in programas]), 200

@catalog_bp.route('/programas/<int:id_programa>', methods=['GET'])
def get_program(id_programa):
    try:
        programa = ProgramService.get_program_by_id(id_programa, active_only=True)
        return jsonify(programa.to_dict()), 200
    except EntityNotFoundException as e:
        return jsonify({'error': str(e)}), 404

@catalog_bp.route('/programas/<int:id_programa>', methods=['PUT'])
def update_program(id_programa):
    data = request.get_json() or {}
    try:
        programa = ProgramService.update_program(
            id_programa=id_programa,
            nombre=data.get('nombre'),
            descripcion=data.get('descripcion')
        )
        return jsonify(programa.to_dict()), 200
    except EntityNotFoundException as e:
        return jsonify({'error': str(e)}), 404
    except InvalidDataException as e:
        return jsonify({'error': str(e)}), 400

@catalog_bp.route('/programas/<int:id_programa>', methods=['DELETE'])
def delete_program(id_programa):
    try:
        res = ProgramService.delete_program(id_programa)
        return jsonify(res), 200
    except EntityNotFoundException as e:
        return jsonify({'error': str(e)}), 404


# --- ENDPOINTS ASOCIACIÓN SOFTWARE-EQUIPO (MUCHOS A MUCHOS) ---

@catalog_bp.route('/equipos/<int:id_equipo>/software', methods=['POST'])
def assign_software(id_equipo):
    data = request.get_json() or {}
    id_programa = data.get('id_programa')
    
    if not id_programa:
        return jsonify({'error': 'El campo id_programa es requerido.'}), 400
        
    try:
        equipo = EquipmentService.assign_software(id_equipo, id_programa)
        return jsonify(equipo.to_dict()), 200
    except EntityNotFoundException as e:
        return jsonify({'error': str(e)}), 404
    except InvalidDataException as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Error interno del servidor.'}), 500

@catalog_bp.route('/equipos/<int:id_equipo>/software/<int:id_programa>', methods=['DELETE'])
def remove_software(id_equipo, id_programa):
    try:
        res = EquipmentService.remove_software(id_equipo, id_programa)
        return jsonify(res), 200
    except EntityNotFoundException as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': 'Error interno del servidor.'}), 500
