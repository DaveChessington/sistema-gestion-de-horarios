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
    assert data['grid'][0]['id_reserva'] == data['grid'][0]['id_evento']


def test_schedule_grid_only_exposes_active_confirmed_reservations(client, db_session):
    confirmed, event = persist_confirmed_request(db_session, 101, 10)
    persist_request(db_session, 102, 11, state='PENDIENTE')
    persist_confirmed_request(db_session, 103, 12, active=False)

    response = client.get('/api/v1/schedule/grid')

    assert response.status_code == 200
    data = response.get_json()
    assert data['total'] == 1
    assert data['grid'][0]['id_peticion'] == confirmed.id_peticion
    assert data['grid'][0]['id_reserva'] == event.id_evento
    assert data['grid'][0]['estado'] == 'APROBADA'


@patch('booking.app.services.booking_service.requests.get')
def test_schedule_grid_filters_confirmed_reservations_by_plantel(
    mock_get, client, db_session
):
    allowed, _ = persist_confirmed_request(db_session, 101, 10)
    persist_confirmed_request(db_session, 202, 11)
    mock_get.return_value = catalog_response([
        {'id_salon': 101, 'id_plantel': 1},
        {'id_salon': 202, 'id_plantel': 2},
    ])

    response = client.get('/api/v1/schedule/grid?id_plantel=1')

    assert response.status_code == 200
    data = response.get_json()
    assert data['total'] == 1
    assert data['grid'][0]['id_peticion'] == allowed.id_peticion


def test_booking_detail_is_limited_to_owner_or_administrator(client, db_session):
    request_record, _ = persist_confirmed_request(db_session, 101, 10)
    owner_token = make_token(id_usuario=10, rol='DOCENTE')
    other_token = make_token(id_usuario=11, rol='DOCENTE')

    allowed = client.get(
        f'/api/v1/booking/request/{request_record.id_peticion}',
        headers={'Authorization': f'Bearer {owner_token}'},
    )
    forbidden = client.get(
        f'/api/v1/booking/request/{request_record.id_peticion}',
        headers={'Authorization': f'Bearer {other_token}'},
    )

    assert allowed.status_code == 200
    assert allowed.get_json()['peticion']['id_peticion'] == request_record.id_peticion
    assert forbidden.status_code == 403


@patch('booking.app.services.booking_service.requests.get')
def test_booking_can_be_reprogrammed_and_updates_confirmed_event(
    mock_get, client, db_session
):
    request_record, event = persist_confirmed_request(db_session, 101, 10)
    mock_get.return_value = catalog_response({
        'id_salon': 102,
        'id_plantel': 1,
        'capacidad': 40,
    })
    token = make_token(id_usuario=10, rol='DOCENTE')

    response = client.patch(
        f'/api/v1/booking/request/{request_record.id_peticion}',
        json={
            'id_salon': 102,
            'fecha_reserva': '2026-10-21',
            'hora_inicio': '16:00',
            'hora_fin': '16:50',
            'id_tipo_evento': 1,
            'materia_nombre': 'Redes reprogramada',
            'numero_alumnos': 30,
        },
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 200
    updated = db_session.session.get(Peticion, request_record.id_peticion)
    updated_event = db_session.session.get(Evento, event.id_evento)
    assert updated.id_salon == 102
    assert updated.fecha == date(2026, 10, 21)
    assert updated.hora_inicio == time(16, 0)
    assert updated.materia_nombre == 'Redes reprogramada'
    assert updated_event.id_salon == 102
    assert updated_event.fecha == date(2026, 10, 21)
    assert updated_event.activo is True


@patch('booking.app.services.booking_service.requests.get')
def test_reprogramming_conflict_keeps_original_reservation_unchanged(
    mock_get, client, db_session
):
    current, current_event = persist_confirmed_request(db_session, 101, 10)
    conflict, _ = persist_confirmed_request(db_session, 102, 11)
    conflict.prioridad_calculada = 90
    db_session.session.commit()
    mock_get.return_value = catalog_response({
        'id_salon': 102,
        'id_plantel': 1,
        'capacidad': 40,
    })
    token = make_token(id_usuario=10, rol='DOCENTE')

    response = client.patch(
        f'/api/v1/booking/request/{current.id_peticion}',
        json={
            'id_salon': 102,
            'fecha_reserva': '2026-10-20',
            'hora_inicio': '08:00',
            'hora_fin': '08:50',
            'id_tipo_evento': 1,
        },
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 409
    unchanged = db_session.session.get(Peticion, current.id_peticion)
    unchanged_event = db_session.session.get(Evento, current_event.id_evento)
    assert unchanged.id_salon == 101
    assert unchanged_event.id_salon == 101
    assert conflict.estado == 'APROBADA'


@patch('booking.app.services.booking_service.requests.get')
def test_admin_plantel_cannot_create_booking_in_another_plantel(
    mock_get, client, db_session
):
    mock_get.return_value = catalog_response({
        'id_salon': 20,
        'id_plantel': 2,
        'capacidad': 40,
    })
    token = make_token(id_usuario=30, rol='ADMIN_PLANTEL', id_plantel_asignado=1)

    response = client.post('/api/v1/booking/request', json={
        'id_salon': 20,
        'fecha_reserva': '2026-10-20',
        'hora_inicio': '08:00',
        'hora_fin': '08:50',
        'id_tipo_evento': 1,
    }, headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 403
    assert 'otro Plantel' in response.get_json()['error']
    assert Peticion.query.count() == 0


@patch('booking.app.services.booking_service.requests.get')
def test_admin_plantel_can_create_booking_in_assigned_plantel(
    mock_get, client, db_session
):
    mock_get.return_value = catalog_response({
        'id_salon': 10,
        'id_plantel': 1,
        'capacidad': 40,
    })
    token = make_token(id_usuario=30, rol='ADMIN_PLANTEL', id_plantel_asignado=1)

    response = client.post('/api/v1/booking/request', json={
        'id_salon': 10,
        'fecha_reserva': '2026-10-20',
        'hora_inicio': '08:00',
        'hora_fin': '08:50',
        'id_tipo_evento': 1,
    }, headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 201
    assert response.get_json()['peticion']['id_salon'] == 10


@patch('booking.app.services.booking_service.requests.get')
def test_admin_plantel_history_only_contains_assigned_plantel_rooms(
    mock_get, client, db_session
):
    allowed_request = persist_request(db_session, room_id=10, user_id=40)
    inactive_room_request = persist_request(db_session, room_id=11, user_id=42)
    persist_request(db_session, room_id=20, user_id=41)
    mock_get.return_value = catalog_response([
        {'id_salon': 10, 'id_plantel': 1, 'activo': True},
        {'id_salon': 11, 'id_plantel': 1, 'activo': False},
        {'id_salon': 20, 'id_plantel': 2, 'activo': True},
    ])
    token = make_token(id_usuario=30, rol='ADMIN_PLANTEL', id_plantel_asignado=1)

    response = client.get(
        '/api/v1/booking/history',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data['total'] == 2
    assert {record['id_peticion'] for record in data['peticiones']} == {
        allowed_request.id_peticion,
        inactive_room_request.id_peticion,
    }
    mock_get.assert_called_once_with(
        'http://127.0.0.1:5002/api/v1/salones',
        params={'active_only': 'false', 'id_plantel': 1},
        timeout=5,
    )


@patch('booking.app.services.booking_service.requests.get')
def test_admin_plantel_history_requires_assigned_plantel(
    mock_get, client, db_session
):
    persist_request(db_session, room_id=10, user_id=40)
    token = make_token(
        id_usuario=30,
        rol='ADMIN_PLANTEL',
        id_plantel_asignado=None,
    )

    response = client.get(
        '/api/v1/booking/history',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 403
    assert 'no tiene un Plantel asignado' in response.get_json()['error']
    mock_get.assert_not_called()


@patch('booking.app.services.booking_service.requests.get')
def test_admin_plantel_history_fails_closed_when_catalog_is_unavailable(
    mock_get, client, db_session
):
    persist_request(db_session, room_id=10, user_id=40)
    mock_get.side_effect = requests.exceptions.ConnectionError('Catalog unavailable')
    token = make_token(id_usuario=30, rol='ADMIN_PLANTEL', id_plantel_asignado=1)

    response = client.get(
        '/api/v1/booking/history',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 503
    assert 'validar el alcance' in response.get_json()['error']


@patch('booking.app.services.booking_service.requests.get')
def test_coordinator_history_remains_global_without_catalog_lookup(
    mock_get, client, db_session
):
    persist_request(db_session, room_id=10, user_id=40)
    persist_request(db_session, room_id=20, user_id=41)
    token = make_token(id_usuario=1, rol='COORDINADOR')

    response = client.get(
        '/api/v1/booking/history',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 200
    assert response.get_json()['total'] == 2
    mock_get.assert_not_called()


@patch('booking.app.services.booking_service.requests.get')
def test_regular_user_history_remains_limited_to_own_requests(
    mock_get, client, db_session
):
    own_request = persist_request(db_session, room_id=10, user_id=40)
    persist_request(db_session, room_id=10, user_id=41)
    token = make_token(id_usuario=40, rol='DOCENTE')

    response = client.get(
        '/api/v1/booking/history',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data['total'] == 1
    assert data['peticiones'][0]['id_peticion'] == own_request.id_peticion
    mock_get.assert_not_called()


@patch('booking.app.services.booking_service.requests.get')
def test_admin_plantel_cannot_cancel_booking_from_another_plantel(
    mock_get, client, db_session
):
    request_record = persist_request(db_session, room_id=20, user_id=41)
    mock_get.return_value = catalog_response([
        {'id_salon': 10, 'id_plantel': 1, 'activo': True},
    ])
    token = make_token(id_usuario=30, rol='ADMIN_PLANTEL', id_plantel_asignado=1)

    response = client.delete(
        f'/api/v1/booking/request/{request_record.id_peticion}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 403
    assert 'otro Plantel' in response.get_json()['error']
    assert db_session.session.get(Peticion, request_record.id_peticion).estado == 'APROBADA'


@patch('booking.app.services.booking_service.requests.get')
def test_admin_plantel_can_cancel_booking_from_assigned_plantel(
    mock_get, client, db_session
):
    request_record = persist_request(db_session, room_id=10, user_id=41)
    mock_get.return_value = catalog_response([
        {'id_salon': 10, 'id_plantel': 1, 'activo': True},
    ])
    token = make_token(id_usuario=30, rol='ADMIN_PLANTEL', id_plantel_asignado=1)

    response = client.delete(
        f'/api/v1/booking/request/{request_record.id_peticion}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 200
    assert db_session.session.get(Peticion, request_record.id_peticion).estado == 'CANCELADA'


@patch('booking.app.services.booking_service.requests.get')
def test_admin_plantel_cancel_fails_closed_when_catalog_is_unavailable(
    mock_get, client, db_session
):
    request_record = persist_request(db_session, room_id=10, user_id=41)
    mock_get.side_effect = requests.exceptions.Timeout('Catalog timeout')
    token = make_token(id_usuario=30, rol='ADMIN_PLANTEL', id_plantel_asignado=1)

    response = client.delete(
        f'/api/v1/booking/request/{request_record.id_peticion}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 503
    assert db_session.session.get(Peticion, request_record.id_peticion).estado == 'APROBADA'


@patch('booking.app.services.booking_service.requests.get')
def test_coordinator_can_cancel_any_plantel_without_catalog_lookup(
    mock_get, client, db_session
):
    request_record = persist_request(db_session, room_id=20, user_id=41)
    token = make_token(id_usuario=1, rol='COORDINADOR')

    response = client.delete(
        f'/api/v1/booking/request/{request_record.id_peticion}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 200
    assert db_session.session.get(Peticion, request_record.id_peticion).estado == 'CANCELADA'
    mock_get.assert_not_called()


@patch('booking.app.services.booking_service.requests.get')
def test_booking_cannot_cancel_a_terminal_request(
    mock_get, client, db_session
):
    request_record = persist_request(
        db_session,
        room_id=20,
        user_id=41,
        state='RECHAZADA',
    )
    token = make_token(id_usuario=1, rol='COORDINADOR')

    response = client.delete(
        f'/api/v1/booking/request/{request_record.id_peticion}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 409
    assert 'estado actual es RECHAZADA' in response.get_json()['error']
    assert db_session.session.get(Peticion, request_record.id_peticion).estado == 'RECHAZADA'
    mock_get.assert_not_called()
