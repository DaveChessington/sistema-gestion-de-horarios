from datetime import date, datetime, time
from unittest.mock import MagicMock, patch

import pytest
import requests

from booking.tests.conftest import make_token
from booking.app.models.evento import Evento
from booking.app.models.peticion import Peticion


def persist_request(db_session, room_id, user_id, state='APROBADA'):
    request_record = Peticion(
        fecha_solicitud=datetime(2026, 8, 16, 10, 0),
        fecha=date(2026, 10, 20),
        hora_inicio=time(8, 0),
        hora_fin=time(8, 50),
        estado=state,
        id_usuario=user_id,
        id_responsable=user_id,
        id_salon=room_id,
        id_tipo_evento=1,
        prioridad_calculada=80,
    )
    db_session.session.add(request_record)
    db_session.session.commit()
    return request_record


def catalog_response(records, status_code=200):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = records
    return response


def persist_confirmed_request(db_session, room_id, user_id, state='APROBADA', active=True):
    request_record = persist_request(db_session, room_id, user_id, state)
    event = Evento(
        nombre='Reserva confirmada',
        fecha=request_record.fecha,
        hora_inicio=request_record.hora_inicio,
        hora_fin=request_record.hora_fin,
        id_salon=room_id,
        id_tipo_evento=1,
        id_usuario=user_id,
        id_peticion=request_record.id_peticion,
        prioridad=request_record.prioridad_calculada,
        activo=active,
    )
    db_session.session.add(event)
    db_session.session.flush()
    request_record.id_evento = event.id_evento
    db_session.session.commit()
    return request_record, event


@patch('booking.app.services.booking_service.requests.get')
def test_booking_request_success(mock_get, client, db_session):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {'id_salon': 1, 'capacidad': 100}
    """Prueba que un docente pueda registrar exitosamente un apartado en un horario libre (201 Created)."""
    token = make_token(id_usuario=10, rol='DOCENTE')
    headers = {'Authorization': f'Bearer {token}'}

    payload = {
        'id_salon': 1,
        'id_programa': 10,
        'materia_nombre': 'Programación Avanzada',
        'fecha_reserva': '2026-10-01',
        'hora_inicio': '08:00',
        'hora_fin': '10:00',
        'id_tipo_evento': 1,  # Clase Curricular (E=50, U=40 -> P=90)
        'observaciones': 'Aula equipada'
    }

    res = client.post('/api/v1/booking/request', json=payload, headers=headers)
    assert res.status_code == 201
    data = res.get_json()
    assert 'peticion' in data
    assert data['peticion']['estado'] in ['APROBADA', 'APARTADA']
    assert data['peticion']['prioridad_calculada'] == 90
    assert data['peticion']['materia_nombre'] == 'Programación Avanzada'


@patch('booking.app.services.booking_service.requests.get')
def test_booking_request_missing_fields(mock_get, client, db_session):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {'id_salon': 1, 'capacidad': 100}
    """Prueba la validación de campos obligatorios (400 Bad Request)."""
    token = make_token(id_usuario=10, rol='DOCENTE')
    headers = {'Authorization': f'Bearer {token}'}

    payload = {
        'id_salon': 1,
        'fecha_reserva': '2026-10-01'
        # faltan hora_inicio, hora_fin, id_tipo_evento
    }

    res = client.post('/api/v1/booking/request', json=payload, headers=headers)
    assert res.status_code == 400
    data = res.get_json()
    assert 'error' in data


@patch('booking.app.services.booking_service.requests.get')
def test_booking_request_invalid_hours(mock_get, client, db_session):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {'id_salon': 1, 'capacidad': 100}
    """Prueba la validación de formato/consistencia de horas (hora_inicio >= hora_fin) -> 400 Bad Request."""
    token = make_token(id_usuario=10, rol='DOCENTE')
    headers = {'Authorization': f'Bearer {token}'}

    payload = {
        'id_salon': 1,
        'fecha_reserva': '2026-10-01',
        'hora_inicio': '12:00',
        'hora_fin': '10:00',  # Hora fin menor que inicio
        'id_tipo_evento': 1
    }

    res = client.post('/api/v1/booking/request', json=payload, headers=headers)
    assert res.status_code == 400


@patch('booking.app.services.booking_service.requests.get')
def test_booking_collision_rejected_fifo(mock_get, client, db_session):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {'id_salon': 2, 'capacidad': 100}
    """
    Prueba que una solicitud de menor prioridad compitiendo con un horario apartado
    sea rechazada con HTTP 409 Conflict (Regla FIFO).
    """
    # 1. Docente aparta primero (P = 40 + 50 = 90)
    token_docente = make_token(id_usuario=10, rol='DOCENTE')
    res1 = client.post('/api/v1/booking/request', json={
        'id_salon': 2,
        'fecha_reserva': '2026-10-02',
        'hora_inicio': '09:00',
        'hora_fin': '11:00',
        'id_tipo_evento': 1
    }, headers={'Authorization': f'Bearer {token_docente}'})
    assert res1.status_code == 201

    # 2. Alumno intenta apartar en el mismo horario (P = 10 + 10 = 20)
    token_alumno = make_token(id_usuario=20, rol='ALUMNO')
    res2 = client.post('/api/v1/booking/request', json={
        'id_salon': 2,
        'fecha_reserva': '2026-10-02',
        'hora_inicio': '10:00',  # Traslape de 10:00 a 11:00
        'hora_fin': '12:00',
        'id_tipo_evento': 4
    }, headers={'Authorization': f'Bearer {token_alumno}'})

    assert res2.status_code == 409
    data2 = res2.get_json()
    assert 'motivo_rechazo' in data2
    assert data2['peticion']['estado'] == 'RECHAZADA'


@patch('booking.app.services.booking_service.requests.get')
def test_booking_collision_displacement_higher_priority(mock_get, client, db_session):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {'id_salon': 3, 'capacidad': 100}
    """
    Prueba que una solicitud entrante con MAYOR PRIORIDAD (Docente, P=90)
    desplace una reserva preexistente de menor prioridad (Alumno, P=20).
    """
    # 1. Alumno aparta primero el salón (P = 10 + 10 = 20)
    token_alumno = make_token(id_usuario=20, rol='ALUMNO')
    res1 = client.post('/api/v1/booking/request', json={
        'id_salon': 3,
        'fecha_reserva': '2026-10-03',
        'hora_inicio': '14:00',
        'hora_fin': '16:00',
        'id_tipo_evento': 4
    }, headers={'Authorization': f'Bearer {token_alumno}'})
    assert res1.status_code == 201
    id_peticion_alumno = res1.get_json()['peticion']['id_peticion']

    # 2. Docente entra con Clase Curricular (P = 40 + 50 = 90) en el mismo horario
    token_docente = make_token(id_usuario=10, rol='DOCENTE')
    res2 = client.post('/api/v1/booking/request', json={
        'id_salon': 3,
        'fecha_reserva': '2026-10-03',
        'hora_inicio': '14:30',
        'hora_fin': '15:30',
        'id_tipo_evento': 1
    }, headers={'Authorization': f'Bearer {token_docente}'})

    assert res2.status_code == 201
    data2 = res2.get_json()
    assert data2['peticion']['estado'] in ['APROBADA', 'APARTADA']

    # 3. Verificar que la petición del alumno pasó a estado 'DESPLAZADA'
    peticion_alumno = db_session.session.get(Peticion, id_peticion_alumno)
    assert peticion_alumno.estado == 'DESPLAZADA'


@patch('booking.app.services.booking_service.requests.get')
def test_booking_delete_cancel_request(mock_get, client, db_session):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {'id_salon': 4, 'capacidad': 100}
    """Prueba la cancelación de una reserva existente vía DELETE."""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {'id_salon': 4, 'capacidad': 100}
    token_docente = make_token(id_usuario=10, rol='DOCENTE')
    headers = {'Authorization': f'Bearer {token_docente}'}

    res_create = client.post('/api/v1/booking/request', json={
        'id_salon': 4,
        'fecha_reserva': '2026-10-10',
        'hora_inicio': '10:00',
        'hora_fin': '12:00',
        'id_tipo_evento': 1
    }, headers=headers)
    assert res_create.status_code == 201
    id_peticion = res_create.get_json()['peticion']['id_peticion']

    # Cancelar la reserva
    res_delete = client.delete(f'/api/v1/booking/request/{id_peticion}', headers=headers)
    assert res_delete.status_code == 200
    assert 'cancelada exitosamente' in res_delete.get_json()['message']

    peticion = db_session.session.get(Peticion, id_peticion)
    assert peticion.estado == 'CANCELADA'


@patch('booking.app.services.booking_service.requests.get')
def test_booking_capacity_validation(mock_get, client, db_session):
    """Prueba que el sistema valide correctamente la capacidad del salón."""
    token = make_token(id_usuario=10, rol='DOCENTE')
    headers = {'Authorization': f'Bearer {token}'}

    # Configurar mock para simular respuesta del servicio Catalog
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        'id_salon': 1,
        'capacidad': 30
    }

    # 1. Petición con más alumnos que capacidad (debe fallar)
    payload_excede = {
        'id_salon': 1,
        'fecha_reserva': '2026-10-15',
        'hora_inicio': '08:00',
        'hora_fin': '10:00',
        'id_tipo_evento': 1,
        'numero_alumnos': 35
    }
    res_excede = client.post('/api/v1/booking/request', json=payload_excede, headers=headers)
    assert res_excede.status_code == 400
    assert 'menor a los alumnos esperados' in res_excede.get_json()['error']

    # 2. Petición con alumnos dentro de la capacidad (debe pasar)
    payload_ok = {
        'id_salon': 1,
        'fecha_reserva': '2026-10-16',
        'hora_inicio': '08:00',
        'hora_fin': '10:00',
        'id_tipo_evento': 1,
        'numero_alumnos': 25
    }
    res_ok = client.post('/api/v1/booking/request', json=payload_ok, headers=headers)
    assert res_ok.status_code == 201


@patch('booking.app.services.booking_service.requests.get')
def test_booking_auto_assign_salon(mock_get, client, db_session):
    """Prueba la asignación automática de salón basada en numero_alumnos cuando id_salon se omite."""
    token = make_token(id_usuario=10, rol='DOCENTE')
    headers = {'Authorization': f'Bearer {token}'}

    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = [
        {'id_salon': 10, 'capacidad': 20},
        {'id_salon': 20, 'capacidad': 50},
        {'id_salon': 30, 'capacidad': 100}
    ]

    payload = {
        'fecha_reserva': '2026-10-20',
        'hora_inicio': '10:00',
        'hora_fin': '12:00',
        'id_tipo_evento': 1,
        'numero_alumnos': 40
    }
    res = client.post('/api/v1/booking/request', json=payload, headers=headers)
    assert res.status_code == 201
    data = res.get_json()
    assert data['peticion']['id_salon'] == 20  # Asigna el salón con capacidad 50 (el óptimo >= 40)


@patch('booking.app.services.booking_service.requests.get')
def test_schedule_grid_query(mock_get, client, db_session):
    """Prueba la consulta de la cuadrícula/matriz de horarios ocupados."""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {'id_salon': 101, 'capacidad': 100}

    token_docente = make_token(id_usuario=10, rol='DOCENTE')
    headers = {'Authorization': f'Bearer {token_docente}'}

    res_create = client.post('/api/v1/booking/request', json={
        'id_salon': 101,
        'fecha_reserva': '2026-10-15',
        'hora_inicio': '08:00',
        'hora_fin': '10:00',
        'id_tipo_evento': 1,
        'materia_nombre': 'Redes'
    }, headers=headers)
    assert res_create.status_code == 201

    res_grid = client.get('/api/v1/schedule/grid?fecha_reserva=2026-10-15&id_salon=101')
    assert res_grid.status_code == 200
    data = res_grid.get_json()
    assert data['total'] == 1
    assert data['grid'][0]['materia_nombre'] == 'Redes'


@patch('booking.app.services.booking_service.requests.get')
def test_booking_non_overlapping_same_salon(mock_get, client, db_session):
    """Prueba que peticiones en el mismo salón a distintas horas sin traslape se aprueben correctamente."""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {'id_salon': 1, 'capacidad': 40}

    token = make_token(id_usuario=10, rol='DOCENTE')
    headers = {'Authorization': f'Bearer {token}'}

    # Petición 1: 08:00 a 10:00
    res1 = client.post('/api/v1/booking/request', json={
        'id_salon': 1,
        'id_programa': 1,
        'fecha_reserva': '2026-10-25',
        'hora_inicio': '08:00',
        'hora_fin': '10:00',
        'id_tipo_evento': 1,
        'numero_alumnos': 20
    }, headers=headers)
    assert res1.status_code == 201

    # Petición 2: 10:00 a 12:00 (Mismo salón y fecha, distinto horario no traslapado)
    res2 = client.post('/api/v1/booking/request', json={
        'id_salon': 1,
        'id_programa': 1,
        'fecha_reserva': '2026-10-25',
        'hora_inicio': '10:00',
        'hora_fin': '12:00',
        'id_tipo_evento': 1,
        'numero_alumnos': 20
    }, headers=headers)
    assert res2.status_code == 201
    assert res2.get_json()['peticion']['estado'] == 'APROBADA'


@patch('booking.app.services.booking_service.requests.get')
def test_booking_consecutive_hours_same_salon(mock_get, client, db_session):
    """Prueba que múltiples clases consecutivas/seguidas (ej. 08-10, 10-12, 12-14) en el mismo salón se aprueben correctamente sin falsas colisiones."""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {'id_salon': 5, 'capacidad': 40}

    token = make_token(id_usuario=10, rol='DOCENTE')
    headers = {'Authorization': f'Bearer {token}'}

    # Bloque 1: 08:00 - 10:00
    r1 = client.post('/api/v1/booking/request', json={
        'id_salon': 5,
        'fecha_reserva': '2026-11-01',
        'hora_inicio': '08:00',
        'hora_fin': '10:00',
        'id_tipo_evento': 1
    }, headers=headers)
    assert r1.status_code == 201

    # Bloque 2: 10:00 - 12:00 (Seguido inmediatamente al Bloque 1)
    r2 = client.post('/api/v1/booking/request', json={
        'id_salon': 5,
        'fecha_reserva': '2026-11-01',
        'hora_inicio': '10:00',
        'hora_fin': '12:00',
        'id_tipo_evento': 1
    }, headers=headers)
    assert r2.status_code == 201

    # Bloque 3: 12:00 - 14:00 (Seguido inmediatamente al Bloque 2)
    r3 = client.post('/api/v1/booking/request', json={
        'id_salon': 5,
        'fecha_reserva': '2026-11-01',
        'hora_inicio': '12:00',
        'hora_fin': '14:00',
        'id_tipo_evento': 1
    }, headers=headers)
    assert r3.status_code == 201


@patch('booking.app.services.booking_service.requests.get')
def test_booking_partial_overlap_rejection(mock_get, client, db_session):
    """Prueba que un traslape parcial de horas (ej: 08:00-10:00 vs 09:30-11:00) detecte la colisión y la rechace si la prioridad es menor o igual."""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {'id_salon': 6, 'capacidad': 40}

    token_docente = make_token(id_usuario=10, rol='DOCENTE')
    token_alumno = make_token(id_usuario=20, rol='ALUMNO')

    # Docente aparta de 08:00 a 10:00 (P = 90)
    r1 = client.post('/api/v1/booking/request', json={
        'id_salon': 6,
        'fecha_reserva': '2026-11-02',
        'hora_inicio': '08:00',
        'hora_fin': '10:00',
        'id_tipo_evento': 1
    }, headers={'Authorization': f'Bearer {token_docente}'})
    assert r1.status_code == 201

    # Alumno intenta apartar de 09:30 a 11:00 (Traslape parcial entre 09:30 y 10:00, P = 20)
    r2 = client.post('/api/v1/booking/request', json={
        'id_salon': 6,
        'fecha_reserva': '2026-11-02',
        'hora_inicio': '09:30',
        'hora_fin': '11:00',
        'id_tipo_evento': 4
    }, headers={'Authorization': f'Bearer {token_alumno}'})
    assert r2.status_code == 409
    assert r2.get_json()['peticion']['estado'] == 'RECHAZADA'


@patch('booking.app.services.booking_service.requests.get')
def test_booking_fully_contained_overlap_displacement(mock_get, client, db_session):
    """Prueba que un traslape totalmente contenido (ej: 09:00-11:00 dentro de 08:00-12:00) desplace la reserva anterior si la nueva tiene mayor prioridad."""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {'id_salon': 7, 'capacidad': 40}

    token_alumno = make_token(id_usuario=20, rol='ALUMNO')
    token_docente = make_token(id_usuario=10, rol='DOCENTE')

    # Alumno aparta bloque largo de 08:00 a 12:00 (P = 20)
    r1 = client.post('/api/v1/booking/request', json={
        'id_salon': 7,
        'fecha_reserva': '2026-11-03',
        'hora_inicio': '08:00',
        'hora_fin': '12:00',
        'id_tipo_evento': 4
    }, headers={'Authorization': f'Bearer {token_alumno}'})
    assert r1.status_code == 201
    id_peticion_alumno = r1.get_json()['peticion']['id_peticion']

    # Docente aparta bloque interno de 09:00 a 11:00 (P = 90)
    r2 = client.post('/api/v1/booking/request', json={
        'id_salon': 7,
        'fecha_reserva': '2026-11-03',
        'hora_inicio': '09:00',
        'hora_fin': '11:00',
        'id_tipo_evento': 1
    }, headers={'Authorization': f'Bearer {token_docente}'})
    assert r2.status_code == 201
    assert r2.get_json()['peticion']['estado'] == 'APROBADA'

    # Verificar que la reserva del alumno fue desplazada
    pet_alumno = db_session.session.get(Peticion, id_peticion_alumno)
    assert pet_alumno.estado == 'DESPLAZADA'
