from datetime import datetime, date, time
from sqlalchemy import or_, and_
from booking.app.extensions import db
from booking.app.models.peticion import Peticion
from booking.app.models.evento import Evento
from booking.app.models.tipo_evento import TipoEvento
from booking.app.utils.security import get_user_role_weight, get_event_type_weight
from flask import current_app
import requests


GLOBAL_ADMIN_ROLES = {'COORDINADOR', 'ADMINISTRADOR'}


class CatalogScopeUnavailableError(Exception):
    """Catalog no permitió resolver de forma segura el alcance del Plantel."""


def _user_role(current_user: dict) -> str:
    return str(current_user.get('rol', '')).upper()


def _assigned_plantel_id(current_user: dict):
    value = current_user.get('id_plantel_asignado')
    if value is None:
        value = current_user.get('id_plantel')
    try:
        plantel_id = int(value)
    except (TypeError, ValueError):
        return None
    return plantel_id if plantel_id > 0 else None


def _get_plantel_room_ids(plantel_id: int) -> set[int]:
    """Obtiene desde Catalog los Salones del Plantel, incluidos los inactivos."""
    catalog_url = current_app.config.get('CATALOG_SERVICE_URL', 'http://127.0.0.1:5002').rstrip('/')
    timeout = current_app.config.get('CATALOG_REQUEST_TIMEOUT', 5)
    try:
        response = requests.get(
            f'{catalog_url}/api/v1/salones',
            params={'active_only': 'false', 'id_plantel': plantel_id},
            timeout=timeout,
        )
    except requests.exceptions.RequestException as error:
        raise CatalogScopeUnavailableError(
            'No se pudo validar el alcance del Plantel con Catalog.'
        ) from error

    if response.status_code != 200:
        raise CatalogScopeUnavailableError(
            'Catalog no pudo validar los Salones asignados al Plantel.'
        )
    try:
        records = response.json()
    except ValueError as error:
        raise CatalogScopeUnavailableError(
            'Catalog devolvió una respuesta inválida al validar el Plantel.'
        ) from error
    if not isinstance(records, list) or not all(isinstance(record, dict) for record in records):
        raise CatalogScopeUnavailableError(
            'Catalog devolvió un listado de Salones inválido.'
        )

    room_ids = set()
    for record in records:
        try:
            record_plantel_id = int(record.get('id_plantel'))
            room_id = int(record.get('id_salon'))
        except (TypeError, ValueError):
            continue
        if record_plantel_id == plantel_id:
            room_ids.add(room_id)
    return room_ids


def parse_date(date_str):
    """Convierte un string 'YYYY-MM-DD' a objeto date."""
    if isinstance(date_str, date):
        return date_str
    return datetime.strptime(str(date_str), '%Y-%m-%d').date()


def parse_time(time_str):
    """Convierte un string 'HH:MM' o 'HH:MM:SS' a objeto time."""
    if isinstance(time_str, time):
        return time_str
    parts = str(time_str).split(':')
    return time(int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)


def calculate_priority(user_role: str, id_tipo_evento: int) -> tuple[int, int, int]:
    """
    Calcula el puntaje de prioridad P = U + E
    - U: Peso del rol del usuario (Docente=40, Admin=30, Alumno=10)
    - E: Peso del tipo de evento (Clase=50, Evento Inst=40, Conferencia=30, Estudio=10)
    
    Retorna la tupla (P_total, U_peso, E_peso).
    """
    u_weight = get_user_role_weight(user_role)
    
    # Consultar peso E en la BD si existe, de lo contrario fallback
    tipo_ev = db.session.get(TipoEvento, id_tipo_evento)
    if tipo_ev:
        e_weight = tipo_ev.peso_evento
    else:
        e_weight = get_event_type_weight(id_tipo_evento)
        
    p_total = u_weight + e_weight
    return p_total, u_weight, e_weight


def create_booking_request(data: dict, current_user: dict) -> tuple[dict, int]:
    """
    Crea una solicitud de reserva ejecutando verificación atómica y resolución de colisiones.
    
    Proceso:
    1. Bloqueo de filas pesimista (SELECT FOR UPDATE) sobre el salón y fecha.
    2. Evaluación de traslapes de horario (hora_inicio < fin_nuevo y hora_fin > inicio_nuevo).
    3. Cálculo de prioridad P = U + E.
    4. Aplicación de regla de desplazamiento (si P_nueva > P_existentes) o rechazo FIFO (si P_nueva <= P_existente).
    5. Asignación automática de auditoría (fecha_solicitud e id_responsable).
    6. Commit atómico.
    """
    try:
        # Extraer y validar campos obligatorios (aceptar fecha_reserva o fecha)
        id_salon = int(data['id_salon'])
        
        # Validar existencia de salón comunicándose con el Catalog Service
        catalog_url = current_app.config.get('CATALOG_SERVICE_URL', 'http://127.0.0.1:5002')
        try:
            # Aunque no requerimos token para el GET público según las rutas actuales, es buena práctica enviarlo
            # si en el futuro se protege.
            response = requests.get(f"{catalog_url}/api/v1/salones/{id_salon}", timeout=5)
            if response.status_code == 404:
                return {'error': f'El salón con ID {id_salon} no existe o no está activo.'}, 400
            elif response.status_code != 200:
                return {'error': f'Error al validar el salón. Servicio de catálogo respondió con: {response.status_code}'}, 500
            
            salon_data = response.json()
            if _user_role(current_user) == 'ADMIN_PLANTEL':
                assigned_plantel_id = _assigned_plantel_id(current_user)
                if assigned_plantel_id is None:
                    return {'error': 'La cuenta ADMIN_PLANTEL no tiene un Plantel asignado.'}, 403
                if str(salon_data.get('id_plantel')) != str(assigned_plantel_id):
                    return {
                        'error': 'No tienes permisos para reservar Salones de otro Plantel.'
                    }, 403
            numero_alumnos = data.get('numero_alumnos')
            if numero_alumnos is not None:
                numero_alumnos = int(numero_alumnos)
                if salon_data.get('capacidad', 0) < numero_alumnos:
                    return {'error': f'La capacidad del salón ({salon_data.get("capacidad", 0)}) es menor a los alumnos esperados ({numero_alumnos})'}, 400
                    
        except requests.exceptions.RequestException as req_e:
             return {'error': f'No se pudo comunicar con el servicio de catálogo para validar el salón: {str(req_e)}'}, 503
             
        # También aseguramos que la variable exista si entra por el except o no entra en el bloque
        numero_alumnos = int(data.get('numero_alumnos')) if data.get('numero_alumnos') is not None else None

        fecha_val = data.get('fecha_reserva') or data.get('fecha')
        if not fecha_val:
            return {'error': 'El campo fecha_reserva (o fecha) es requerido'}, 400

        fecha_obj = parse_date(fecha_val)
        hora_inicio_obj = parse_time(data['hora_inicio'])
        hora_fin_obj = parse_time(data['hora_fin'])
        
        if hora_inicio_obj >= hora_fin_obj:
            return {'error': 'La hora de inicio debe ser estrictamente menor que la hora de fin'}, 400

        id_tipo_evento = int(data['id_tipo_evento'])
        id_programa = int(data['id_programa']) if data.get('id_programa') is not None else None
        materia_nombre = data.get('materia_nombre')
        observaciones = data.get('observaciones', '')
        numero_alumnos = int(data.get('numero_alumnos')) if data.get('numero_alumnos') is not None else None

        user_role = current_user.get('rol', 'ALUMNO')
        id_usuario = current_user.get('id_usuario')
        id_responsable = id_usuario

        # 2. Calcular Prioridad P = U + E
        prioridad_nueva, u_peso, e_peso = calculate_priority(user_role, id_tipo_evento)

        # 3. Determinar o auto-asignar el id_salon
        catalog_url = current_app.config.get('CATALOG_SERVICE_URL', 'http://127.0.0.1:5002')
        id_salon = data.get('id_salon')

        if id_salon is not None:
            id_salon = int(id_salon)
            try:
                response = requests.get(f"{catalog_url}/api/v1/salones/{id_salon}", timeout=5)
                if response.status_code == 404:
                    return {'error': f'El salón con ID {id_salon} no existe o no está activo.'}, 400
                elif response.status_code != 200:
                    return {'error': f'Error al validar el salón. Servicio de catálogo respondió con: {response.status_code}'}, 500
                
                salon_data = response.json()
                if numero_alumnos is not None and salon_data.get('capacidad', 0) < numero_alumnos:
                    return {'error': f'La capacidad del salón ({salon_data.get("capacidad", 0)}) es menor a los alumnos esperados ({numero_alumnos})'}, 400
            except requests.exceptions.RequestException as req_e:
                return {'error': f'No se pudo comunicar con el servicio de catálogo para validar el salón: {str(req_e)}'}, 503
        else:
            # Auto-asignación de salón basado en capacidad y disponibilidad
            params = {}
            if data.get('id_plantel'):
                params['id_plantel'] = data.get('id_plantel')
            if data.get('software_id'):
                params['software_id'] = data.get('software_id')

            try:
                response = requests.get(f"{catalog_url}/api/v1/salones", params=params, timeout=5)
                if response.status_code != 200:
                    return {'error': f'Error al consultar el catálogo de salones. Servicio de catálogo respondió con: {response.status_code}'}, 500
                
                salones_resp = response.json()
                salones_disponibles = salones_resp if isinstance(salones_resp, list) else [salones_resp]
                
                if not salones_disponibles:
                    return {'error': 'No hay salones disponibles en el catálogo que cumplan los criterios.'}, 400
                
                if numero_alumnos is not None:
                    salones_aptos = [s for s in salones_disponibles if s.get('capacidad', 0) >= numero_alumnos]
                    if not salones_aptos:
                        return {'error': f'No hay salones con capacidad suficiente para los {numero_alumnos} alumnos esperados.'}, 400
                else:
                    salones_aptos = salones_disponibles

                # Ordenar por capacidad ascendente para elegir el salón más adecuado
                salones_aptos.sort(key=lambda s: s.get('capacidad', 0))

                # Buscar entre los salones aptos uno que esté completamente libre en el horario solicitado
                salon_elegido = None
                salon_desplazable = None

                for s in salones_aptos:
                    sid = s['id_salon']
                    traslapes = Peticion.query.filter(
                        Peticion.id_salon == sid,
                        Peticion.fecha == fecha_obj,
                        Peticion.estado.in_(['APROBADA', 'APARTADA', 'PENDIENTE']),
                        Peticion.hora_inicio < hora_fin_obj,
                        Peticion.hora_fin > hora_inicio_obj
                    ).all()

                    if not traslapes:
                        salon_elegido = sid
                        break
                    else:
                        max_p = max(p.prioridad_calculada for p in traslapes)
                        if prioridad_nueva > max_p and salon_desplazable is None:
                            salon_desplazable = sid

                id_salon = salon_elegido or salon_desplazable or salones_aptos[0]['id_salon']
            except requests.exceptions.RequestException as req_e:
                return {'error': f'No se pudo comunicar con el servicio de catálogo para auto-asignar el salón: {str(req_e)}'}, 503

        # 2. Bloqueo de fila atómico (SELECT FOR UPDATE) y consulta de traslapes en el mismo salón y fecha
        query = Peticion.query.filter(
            Peticion.id_salon == id_salon,
            Peticion.fecha == fecha_obj,
            Peticion.estado.in_(['APROBADA', 'APARTADA', 'PENDIENTE']),
            Peticion.hora_inicio < hora_fin_obj,
            Peticion.hora_fin > hora_inicio_obj
        )

        # Usar bloqueo FOR UPDATE si la BD lo soporta (PostgreSQL)
        if db.engine.url.drivername != 'sqlite':
            query = query.with_for_update()

        peticiones_traslapadas = query.all()

        # 3. Evaluar colisiones
        if not peticiones_traslapadas:
            # Caso 1: Espacio totalmente libre -> Aprobación directa 'APROBADA'
            nueva_peticion = Peticion(
                fecha_solicitud=datetime.utcnow(),
                fecha=fecha_obj,
                hora_inicio=hora_inicio_obj,
                hora_fin=hora_fin_obj,
                estado='APROBADA',
                id_usuario=id_usuario,
                id_responsable=id_responsable,
                id_salon=id_salon,
                id_programa=id_programa,
                materia_nombre=materia_nombre,
                numero_alumnos=numero_alumnos,
                id_tipo_evento=id_tipo_evento,
                prioridad_calculada=prioridad_nueva,
                observaciones=observaciones
            )
            db.session.add(nueva_peticion)
            db.session.flush()

            # Crear Evento confirmado asociado
            nombre_evento = materia_nombre or f"Reserva Salón {id_salon} ({data.get('nombre_evento', 'Evento')})"
            nuevo_evento = Evento(
                nombre=nombre_evento,
                descripcion=observaciones,
                fecha=fecha_obj,
                hora_inicio=hora_inicio_obj,
                hora_fin=hora_fin_obj,
                id_salon=id_salon,
                numero_alumnos=numero_alumnos,
                id_tipo_evento=id_tipo_evento,
                id_usuario=id_usuario,
                id_peticion=nueva_peticion.id_peticion,
                prioridad=prioridad_nueva,
                activo=True
            )
            db.session.add(nuevo_evento)
            db.session.flush()

            nueva_peticion.id_evento = nuevo_evento.id_evento
            db.session.commit()

            return {
                'message': 'Reserva aprobada y registrada exitosamente.',
                'peticion': nueva_peticion.to_dict()
            }, 201

        else:
            # Caso 2: Existen traslapes. Comparar prioridades.
            max_prioridad_existente = max(p.prioridad_calculada for p in peticiones_traslapadas)

            if prioridad_nueva > max_prioridad_existente:
                # La nueva petición TIENE MAYOR PRIORIDAD -> Desplaza a las existentes de menor prioridad
                for pet in peticiones_traslapadas:
                    pet.estado = 'DESPLAZADA'
                    pet.motivo_rechazo = f"Desplazada por solicitud entrante de mayor prioridad (P={prioridad_nueva} vs P={pet.prioridad_calculada})."
                    
                    # Desactivar evento asociado si existía
                    if pet.id_evento:
                        ev = db.session.get(Evento, pet.id_evento)
                        if ev:
                            ev.activo = False

                # Insertar la nueva petición como APROBADA
                nueva_peticion = Peticion(
                    fecha_solicitud=datetime.utcnow(),
                    fecha=fecha_obj,
                    hora_inicio=hora_inicio_obj,
                    hora_fin=hora_fin_obj,
                    estado='APROBADA',
                    id_usuario=id_usuario,
                    id_responsable=id_responsable,
                    id_salon=id_salon,
                    id_programa=id_programa,
                    materia_nombre=materia_nombre,
                    numero_alumnos=numero_alumnos,
                    id_tipo_evento=id_tipo_evento,
                    prioridad_calculada=prioridad_nueva,
                    observaciones=observaciones
                )
                db.session.add(nueva_peticion)
                db.session.flush()

                # Crear evento para la nueva petición desplazante
                nombre_evento = materia_nombre or f"Reserva Salón {id_salon} ({data.get('nombre_evento', 'Evento Desplazante')})"
                nuevo_evento = Evento(
                    nombre=nombre_evento,
                    descripcion=observaciones,
                    fecha=fecha_obj,
                    hora_inicio=hora_inicio_obj,
                    hora_fin=hora_fin_obj,
                    id_salon=id_salon,
                    numero_alumnos=numero_alumnos,
                    id_tipo_evento=id_tipo_evento,
                    id_usuario=id_usuario,
                    id_peticion=nueva_peticion.id_peticion,
                    prioridad=prioridad_nueva,
                    activo=True
                )
                db.session.add(nuevo_evento)
                db.session.flush()

                nueva_peticion.id_evento = nuevo_evento.id_evento
                db.session.commit()

                return {
                    'message': 'Reserva aprobada por mayor prioridad. Las solicitudes preexistentes fueron desplazadas.',
                    'peticion': nueva_peticion.to_dict()
                }, 201

            else:
                # La nueva petición TIENE MENOR O IGUAL PRIORIDAD -> Rechazo por regla FIFO
                motivo = f"Solicitud rechazada por conflicto de horario con una reserva de mayor o igual prioridad (P={max_prioridad_existente} vs P={prioridad_nueva}) según el criterio FIFO."
                
                nueva_peticion = Peticion(
                    fecha_solicitud=datetime.utcnow(),
                    fecha=fecha_obj,
                    hora_inicio=hora_inicio_obj,
                    hora_fin=hora_fin_obj,
                    estado='RECHAZADA',
                    id_usuario=id_usuario,
                    id_responsable=id_responsable,
                    id_salon=id_salon,
                    id_programa=id_programa,
                    materia_nombre=materia_nombre,
                    numero_alumnos=numero_alumnos,
                    id_tipo_evento=id_tipo_evento,
                    prioridad_calculada=prioridad_nueva,
                    observaciones=observaciones,
                    motivo_rechazo=motivo
                )
                db.session.add(nueva_peticion)
                db.session.commit()

                return {
                    'error': 'Conflicto de reserva: Solicitud rechazada por prioridad o criterio FIFO.',
                    'motivo_rechazo': motivo,
                    'peticion': nueva_peticion.to_dict()
                }, 409

    except ValueError as ve:
        db.session.rollback()
        return {'error': f'Formato de datos inválido: {str(ve)}'}, 400
    except KeyError as ke:
        db.session.rollback()
        return {'error': f'Campo requerido faltante: {str(ke)}'}, 400
    except Exception as e:
        db.session.rollback()
        return {'error': f'Error interno en el servidor: {str(e)}'}, 500


def _booking_access_error(peticion: Peticion, current_user: dict):
    """Valida propiedad o alcance administrativo sobre una petición."""
    user_role = _user_role(current_user)
    user_id = current_user.get('id_usuario')
    if user_role == 'ADMIN_PLANTEL':
        assigned_plantel_id = _assigned_plantel_id(current_user)
        if assigned_plantel_id is None:
            return 'La cuenta ADMIN_PLANTEL no tiene un Plantel asignado.', 403
        try:
            allowed_room_ids = _get_plantel_room_ids(assigned_plantel_id)
        except CatalogScopeUnavailableError as error:
            return str(error), 503
        if peticion.id_salon not in allowed_room_ids:
            return 'No tienes permisos para administrar reservas de otro Plantel.', 403
    elif user_role not in GLOBAL_ADMIN_ROLES and peticion.id_usuario != user_id:
        return 'No tienes permisos suficientes para administrar esta reserva.', 403
    return None


def get_booking_request(id_peticion: int, current_user: dict) -> tuple[dict, int]:
    """Consulta una petición individual con el mismo alcance del historial."""
    peticion = db.session.get(Peticion, id_peticion)
    if peticion is None:
        return {'error': f'Solicitud de reserva #{id_peticion} no encontrada'}, 404
    access_error = _booking_access_error(peticion, current_user)
    if access_error:
        message, status_code = access_error
        return {'error': message}, status_code
    return {'peticion': peticion.to_dict()}, 200


def update_booking_request(
    id_peticion: int,
    data: dict,
    current_user: dict,
) -> tuple[dict, int]:
    """Reprograma una reserva de forma atómica aplicando prioridad y FIFO."""
    try:
        peticion = db.session.get(Peticion, id_peticion)
        if peticion is None:
            return {'error': f'Solicitud de reserva #{id_peticion} no encontrada'}, 404

        access_error = _booking_access_error(peticion, current_user)
        if access_error:
            message, status_code = access_error
            return {'error': message}, status_code
        if peticion.estado not in {'APROBADA', 'APARTADA', 'PENDIENTE'}:
            return {
                'error': (
                    f'La solicitud #{id_peticion} no puede modificarse porque '
                    f'su estado actual es {peticion.estado}.'
                )
            }, 409

        id_salon = int(data.get('id_salon', peticion.id_salon))
        fecha_obj = parse_date(
            data.get('fecha_reserva') or data.get('fecha') or peticion.fecha
        )
        hora_inicio_obj = parse_time(data.get('hora_inicio', peticion.hora_inicio))
        hora_fin_obj = parse_time(data.get('hora_fin', peticion.hora_fin))
        id_tipo_evento = int(data.get('id_tipo_evento', peticion.id_tipo_evento))
        id_programa_value = data.get('id_programa', peticion.id_programa)
        id_programa = int(id_programa_value) if id_programa_value not in {None, ''} else None
        numero_value = data.get('numero_alumnos', peticion.numero_alumnos)
        numero_alumnos = int(numero_value) if numero_value not in {None, ''} else None
        materia_nombre = data.get('materia_nombre', peticion.materia_nombre)
        observaciones = data.get('observaciones', peticion.observaciones) or ''

        if hora_inicio_obj >= hora_fin_obj:
            return {'error': 'La hora de inicio debe ser estrictamente menor que la hora de fin'}, 400
        if numero_alumnos is not None and numero_alumnos <= 0:
            return {'error': 'El número de alumnos debe ser mayor a cero'}, 400

        catalog_url = current_app.config.get(
            'CATALOG_SERVICE_URL',
            'http://127.0.0.1:5002',
        ).rstrip('/')
        timeout = current_app.config.get('CATALOG_REQUEST_TIMEOUT', 5)
        try:
            response = requests.get(
                f'{catalog_url}/api/v1/salones/{id_salon}',
                timeout=timeout,
            )
        except requests.exceptions.RequestException as error:
            return {
                'error': (
                    'No se pudo comunicar con el servicio de catálogo para '
                    f'validar el salón: {str(error)}'
                )
            }, 503
        if response.status_code == 404:
            return {'error': f'El salón con ID {id_salon} no existe o no está activo.'}, 400
        if response.status_code != 200:
            return {'error': 'Catalog no pudo validar el salón seleccionado.'}, 503
        try:
            salon_data = response.json()
        except ValueError:
            return {'error': 'Catalog devolvió un salón inválido.'}, 503

        if _user_role(current_user) == 'ADMIN_PLANTEL':
            if str(salon_data.get('id_plantel')) != str(_assigned_plantel_id(current_user)):
                return {'error': 'No tienes permisos para reprogramar en otro Plantel.'}, 403
        try:
            salon_capacity = int(salon_data.get('capacidad', 0))
        except (TypeError, ValueError):
            salon_capacity = 0
        if numero_alumnos is not None and numero_alumnos > salon_capacity:
            return {
                'error': (
                    f'La capacidad del salón ({salon_capacity}) es menor a los '
                    f'alumnos esperados ({numero_alumnos})'
                )
            }, 400

        prioridad_nueva, _, _ = calculate_priority(
            current_user.get('rol', 'ALUMNO'),
            id_tipo_evento,
        )
        collision_query = Peticion.query.filter(
            Peticion.id_peticion != peticion.id_peticion,
            Peticion.id_salon == id_salon,
            Peticion.fecha == fecha_obj,
            Peticion.estado.in_(['APROBADA', 'APARTADA', 'PENDIENTE']),
            Peticion.hora_inicio < hora_fin_obj,
            Peticion.hora_fin > hora_inicio_obj,
        )
        if db.engine.url.drivername != 'sqlite':
            collision_query = collision_query.with_for_update()
        collisions = collision_query.all()
        if collisions:
            max_priority = max(item.prioridad_calculada for item in collisions)
            if prioridad_nueva <= max_priority:
                return {
                    'error': 'Conflicto de reserva: la reprogramación fue rechazada.',
                    'motivo_rechazo': (
                        'La reserva existente se conservó sin cambios porque existe '
                        f'una solicitud con prioridad mayor o igual (P={max_priority}).'
                    ),
                }, 409
            for displaced in collisions:
                displaced.estado = 'DESPLAZADA'
                displaced.motivo_rechazo = (
                    'Desplazada por una reprogramación de mayor prioridad '
                    f'(P={prioridad_nueva} vs P={displaced.prioridad_calculada}).'
                )
                if displaced.id_evento:
                    displaced_event = db.session.get(Evento, displaced.id_evento)
                    if displaced_event:
                        displaced_event.activo = False

        peticion.fecha = fecha_obj
        peticion.hora_inicio = hora_inicio_obj
        peticion.hora_fin = hora_fin_obj
        peticion.estado = 'APROBADA'
        peticion.id_responsable = current_user.get('id_usuario')
        peticion.id_salon = id_salon
        peticion.id_programa = id_programa
        peticion.materia_nombre = materia_nombre
        peticion.numero_alumnos = numero_alumnos
        peticion.id_tipo_evento = id_tipo_evento
        peticion.prioridad_calculada = prioridad_nueva
        peticion.observaciones = observaciones
        peticion.motivo_rechazo = None

        event = db.session.get(Evento, peticion.id_evento) if peticion.id_evento else None
        if event is None:
            event = Evento(id_peticion=peticion.id_peticion)
            db.session.add(event)
        event.nombre = materia_nombre or f'Reserva Salón {id_salon}'
        event.descripcion = observaciones
        event.fecha = fecha_obj
        event.hora_inicio = hora_inicio_obj
        event.hora_fin = hora_fin_obj
        event.id_salon = id_salon
        event.numero_alumnos = numero_alumnos
        event.id_tipo_evento = id_tipo_evento
        event.id_usuario = peticion.id_usuario
        event.prioridad = prioridad_nueva
        event.activo = True
        db.session.flush()
        peticion.id_evento = event.id_evento
        db.session.commit()
        return {
            'message': f'Reserva #{id_peticion} actualizada exitosamente.',
            'peticion': peticion.to_dict(),
        }, 200
    except (TypeError, ValueError) as error:
        db.session.rollback()
        return {'error': f'Formato de datos inválido: {str(error)}'}, 400
    except Exception as error:
        db.session.rollback()
        return {'error': f'Error interno al actualizar la reserva: {str(error)}'}, 500


def cancel_booking_request(id_peticion: int, current_user: dict) -> tuple[dict, int]:
    """
    Cancela una solicitud de reserva liberando el espacio reservado en la base de datos.
    """
    try:
        peticion = db.session.get(Peticion, id_peticion)
        if not peticion:
            return {'error': f'Solicitud de reserva #{id_peticion} no encontrada'}, 404

        user_role = _user_role(current_user)
        user_id = current_user.get('id_usuario')

        if user_role == 'ADMIN_PLANTEL':
            assigned_plantel_id = _assigned_plantel_id(current_user)
            if assigned_plantel_id is None:
                return {'error': 'La cuenta ADMIN_PLANTEL no tiene un Plantel asignado.'}, 403
            try:
                allowed_room_ids = _get_plantel_room_ids(assigned_plantel_id)
            except CatalogScopeUnavailableError as error:
                return {'error': str(error)}, 503
            if peticion.id_salon not in allowed_room_ids:
                return {
                    'error': 'No tienes permisos para cancelar reservas de otro Plantel.'
                }, 403
        elif user_role not in GLOBAL_ADMIN_ROLES and peticion.id_usuario != user_id:
            return {'error': 'No tienes permisos suficientes para cancelar esta reserva'}, 403

        if peticion.estado not in {'APROBADA', 'APARTADA', 'PENDIENTE'}:
            return {
                'error': (
                    f'La solicitud #{id_peticion} no puede cancelarse porque '
                    f'su estado actual es {peticion.estado}.'
                )
            }, 409

        peticion.estado = 'CANCELADA'
        
        # Liberar evento asociado si existe
        if peticion.id_evento:
            ev = db.session.get(Evento, peticion.id_evento)
            if ev:
                ev.activo = False

        db.session.commit()
        return {
            'message': f'Reserva #{id_peticion} cancelada exitosamente y espacio liberado.',
            'peticion': peticion.to_dict()
        }, 200

    except Exception as e:
        db.session.rollback()
        return {'error': f'Error al cancelar la reserva: {str(e)}'}, 500


def get_booking_history(current_user: dict, filters: dict = None) -> tuple[dict, int]:
    """
    Retorna el historial de peticiones de reserva.
    - COORDINADOR puede ver el historial global o filtrado.
    - ADMIN_PLANTEL solo puede ver solicitudes de Salones de su Plantel.
    - Si el usuario es DOCENTE o ALUMNO, ve únicamente sus propias peticiones.
    """
    try:
        query = Peticion.query
        user_role = _user_role(current_user)
        user_id = current_user.get('id_usuario')

        # Control de acceso por rol
        if user_role == 'ADMIN_PLANTEL':
            assigned_plantel_id = _assigned_plantel_id(current_user)
            if assigned_plantel_id is None:
                return {'error': 'La cuenta ADMIN_PLANTEL no tiene un Plantel asignado.'}, 403
            try:
                allowed_room_ids = _get_plantel_room_ids(assigned_plantel_id)
            except CatalogScopeUnavailableError as error:
                return {'error': str(error)}, 503
            query = query.filter(Peticion.id_salon.in_(allowed_room_ids))
            if filters and filters.get('id_usuario'):
                query = query.filter(Peticion.id_usuario == int(filters['id_usuario']))
        elif user_role not in GLOBAL_ADMIN_ROLES:
            query = query.filter(Peticion.id_usuario == user_id)
        elif filters and filters.get('id_usuario'):
            query = query.filter(Peticion.id_usuario == int(filters['id_usuario']))

        # Filtros opcionales en la consulta
        if filters:
            if filters.get('estado'):
                query = query.filter(Peticion.estado == filters['estado'].upper())
            if filters.get('id_salon'):
                query = query.filter(Peticion.id_salon == int(filters['id_salon']))
            if filters.get('fecha') or filters.get('fecha_reserva'):
                fecha_val = filters.get('fecha_reserva') or filters.get('fecha')
                fecha_obj = parse_date(fecha_val)
                query = query.filter(Peticion.fecha == fecha_obj)

        peticiones = query.order_by(Peticion.fecha_solicitud.desc()).all()
        result = [p.to_dict() for p in peticiones]

        return {
            'total': len(result),
            'peticiones': result
        }, 200

    except Exception as e:
        return {'error': f'Error recuperando el historial: {str(e)}'}, 500


def get_schedule_grid(filters: dict = None) -> tuple[dict, int]:
    """
    Retorna las reservas confirmadas que ocupan la cuadrícula.

    Una Reserva es el Evento activo asociado a una Peticion APROBADA o
    APARTADA. Las peticiones pendientes no bloquean ni se publican como
    ocupación confirmada.

    Filtros opcionales: id_plantel, id_salon, id_programa, fecha / fecha_reserva
    """
    try:
        query = db.session.query(Peticion, Evento).join(
            Evento,
            Peticion.id_evento == Evento.id_evento,
        ).filter(
            Peticion.estado.in_(['APROBADA', 'APARTADA']),
            Evento.activo.is_(True),
        )

        if filters:
            if filters.get('id_plantel'):
                plantel_id = int(filters['id_plantel'])
                if plantel_id <= 0:
                    raise ValueError('id_plantel debe ser un entero positivo')
                room_ids = _get_plantel_room_ids(plantel_id)
                if not room_ids:
                    return {'total': 0, 'grid': []}, 200
                query = query.filter(Evento.id_salon.in_(room_ids))
            if filters.get('id_salon'):
                query = query.filter(Evento.id_salon == int(filters['id_salon']))
            if filters.get('id_programa'):
                query = query.filter(Peticion.id_programa == int(filters['id_programa']))
            if filters.get('fecha') or filters.get('fecha_reserva'):
                fecha_val = filters.get('fecha_reserva') or filters.get('fecha')
                fecha_obj = parse_date(fecha_val)
                query = query.filter(Evento.fecha == fecha_obj)

        reservas = query.order_by(Evento.id_salon.asc(), Evento.hora_inicio.asc()).all()

        grid = []
        for p, reserva in reservas:
            item = p.to_dict()
            grid.append({
                'id_reserva': reserva.id_evento,
                'id_evento': reserva.id_evento,
                'id_peticion': item['id_peticion'],
                'id_salon': reserva.id_salon,
                'fecha_reserva': reserva.fecha.strftime('%Y-%m-%d'),
                'hora_inicio': reserva.hora_inicio.strftime('%H:%M:%S'),
                'hora_fin': reserva.hora_fin.strftime('%H:%M:%S'),
                'estado': item['estado'],
                'materia_nombre': item['materia_nombre'] or reserva.nombre,
                'id_programa': item['id_programa'],
                'id_usuario': reserva.id_usuario,
                'prioridad_calculada': reserva.prioridad,
                'nombre_tipo_evento': (
                    reserva.tipo_evento.nombre if reserva.tipo_evento else None
                ),
            })

        return {
            'total': len(grid),
            'grid': grid
        }, 200

    except CatalogScopeUnavailableError as error:
        return {'error': str(error)}, 503
    except (TypeError, ValueError) as error:
        return {'error': f'Filtro inválido: {str(error)}'}, 400
    except Exception as e:
        return {'error': f'Error al consultar la cuadrícula de horarios: {str(e)}'}, 500
