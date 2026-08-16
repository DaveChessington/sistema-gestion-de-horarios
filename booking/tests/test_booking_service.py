import pytest
from unittest.mock import patch
from booking.tests.conftest import make_token
from booking.app.models.peticion import Peticion


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


def test_booking_delete_cancel_request(client, db_session):
    """Prueba la cancelación de una reserva existente vía DELETE."""
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


def test_schedule_grid_query(client, db_session):
    """Prueba la consulta de la cuadrícula/matriz de horarios ocupados."""
    token_docente = make_token(id_usuario=10, rol='DOCENTE')
    headers = {'Authorization': f'Bearer {token_docente}'}

    client.post('/api/v1/booking/request', json={
        'id_salon': 101,
        'fecha_reserva': '2026-10-15',
        'hora_inicio': '08:00',
        'hora_fin': '10:00',
        'id_tipo_evento': 1,
        'materia_nombre': 'Redes'
    }, headers=headers)

    res_grid = client.get('/api/v1/schedule/grid?fecha_reserva=2026-10-15&id_salon=101')
    assert res_grid.status_code == 200
    data = res_grid.get_json()
    assert data['total'] == 1
    assert data['grid'][0]['materia_nombre'] == 'Redes'
