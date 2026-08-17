from datetime import datetime, date, time
from sqlalchemy import or_, and_
from booking.app.extensions import db
from booking.app.models.peticion import Peticion
from booking.app.models.evento import Evento
from booking.app.models.tipo_evento import TipoEvento
from booking.app.utils.security import get_user_role_weight, get_event_type_weight


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


from flask import current_app
import requests

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
        # 1. Extraer y validar fecha y horas
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


def cancel_booking_request(id_peticion: int, current_user: dict) -> tuple[dict, int]:
    """
    Cancela una solicitud de reserva liberando el espacio reservado en la base de datos.
    """
    try:
        peticion = db.session.get(Peticion, id_peticion)
        if not peticion:
            return {'error': f'Solicitud de reserva #{id_peticion} no encontrada'}, 404

        user_role = str(current_user.get('rol', '')).upper()
        user_id = current_user.get('id_usuario')

        # Permiso: Solo el propietario de la reserva o un administrador/coordinador puede cancelarla
        if user_role not in ['COORDINADOR', 'ADMIN_PLANTEL', 'ADMINISTRADOR'] and peticion.id_usuario != user_id:
            return {'error': 'No tienes permisos suficientes para cancelar esta reserva'}, 403

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
    - Si el usuario es COORDINADOR o ADMIN_PLANTEL, puede ver el historial global o filtrado.
    - Si el usuario es DOCENTE o ALUMNO, ve únicamente sus propias peticiones.
    """
    try:
        query = Peticion.query
        user_role = str(current_user.get('rol', '')).upper()
        user_id = current_user.get('id_usuario')

        # Control de acceso por rol
        if user_role not in ['COORDINADOR', 'ADMIN_PLANTEL', 'ADMINISTRADOR']:
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
    Retorna la cuadrícula/matriz de horarios ocupados en formato JSON.
    Filtros opcionales: id_plantel, id_salon, fecha / fecha_reserva
    """
    try:
        query = Peticion.query.filter(Peticion.estado.in_(['APROBADA', 'APARTADA', 'PENDIENTE']))

        if filters:
            if filters.get('id_salon'):
                query = query.filter(Peticion.id_salon == int(filters['id_salon']))
            if filters.get('fecha') or filters.get('fecha_reserva'):
                fecha_val = filters.get('fecha_reserva') or filters.get('fecha')
                fecha_obj = parse_date(fecha_val)
                query = query.filter(Peticion.fecha == fecha_obj)

        peticiones = query.order_by(Peticion.id_salon.asc(), Peticion.hora_inicio.asc()).all()

        grid = []
        for p in peticiones:
            item = p.to_dict()
            grid.append({
                'id_peticion': item['id_peticion'],
                'id_salon': item['id_salon'],
                'fecha_reserva': item['fecha_reserva'],
                'hora_inicio': item['hora_inicio'],
                'hora_fin': item['hora_fin'],
                'estado': item['estado'],
                'materia_nombre': item['materia_nombre'],
                'id_programa': item['id_programa'],
                'id_usuario': item['id_usuario'],
                'prioridad_calculada': item['prioridad_calculada'],
                'nombre_tipo_evento': item['nombre_tipo_evento']
            })

        return {
            'total': len(grid),
            'grid': grid
        }, 200

    except Exception as e:
        return {'error': f'Error al consultar la cuadrícula de horarios: {str(e)}'}, 500
