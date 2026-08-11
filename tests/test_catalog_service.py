import pytest

from catalog.app.services.catalog_service import (
    CampusService,
    DuplicateEntityException,
    EntityNotFoundException,
    EquipmentService,
    InvalidDataException,
    ProgramService,
)


def test_create_plantel_success(db_session, app):
    with app.app_context():
        plantel = CampusService.create_plantel('Plantel X', direccion='Dirección X')
        assert plantel.id is not None
        assert plantel.nombre == 'Plantel X'


def test_create_plantel_invalid_name(db_session, app):
    with app.app_context():
        with pytest.raises(InvalidDataException):
            CampusService.create_plantel('   ')


def test_create_salon_and_list(db_session, app):
    with app.app_context():
        plantel = CampusService.create_plantel('Plantel Y')
        salon = CampusService.create_salon('101', 'Aula 101', 25, plantel.id)
        assert salon.id_salon is not None
        assert salon.numero == '101'
        salones = CampusService.list_salones(id_plantel=plantel.id)
        assert any(s.id_salon == salon.id_salon for s in salones)


def test_create_equipment_duplicate(db_session, app):
    with app.app_context():
        plantel = CampusService.create_plantel('Plantel Z')
        salon = CampusService.create_salon('201', 'Aula 201', 20, plantel.id)
        e1 = EquipmentService.create_equipment('EQ-001', 'Equipo 1', id_salon=salon.id_salon)
        assert e1.id_equipo is not None
        with pytest.raises(DuplicateEntityException):
            EquipmentService.create_equipment('EQ-001', 'Equipo duplicado')


def test_assign_and_remove_software(db_session, app):
    with app.app_context():
        programa = ProgramService.create_program('Programa A')
        plantel = CampusService.create_plantel('Plantel W')
        salon = CampusService.create_salon('301', 'Aula 301', 15, plantel.id)
        equipo = EquipmentService.create_equipment('EQ-002', 'Equipo 2', id_salon=salon.id_salon)

        equipo = EquipmentService.assign_software(equipo.id_equipo, programa.id_programa)
        assert any(p.id_programa == programa.id_programa for p in equipo.programas)

        res = EquipmentService.remove_software(equipo.id_equipo, programa.id_programa)
        assert 'desinstalado' in res['message']


def test_get_nonexistent_entities(db_session, app):
    with app.app_context():
        with pytest.raises(EntityNotFoundException):
            CampusService.get_plantel_by_id(999999)
        with pytest.raises(EntityNotFoundException):
            ProgramService.get_program_by_id(999999)


def test_public_get_endpoints_no_auth(db_session, app, client):
    with app.app_context():
        plantel = CampusService.create_plantel('Plantel Público')
        salon = CampusService.create_salon('101', 'Aula pública', 20, plantel.id)
        programa = ProgramService.create_program('Programa Público')
        EquipmentService.create_equipment('EQ-100', 'Equipo público', id_salon=salon.id_salon)

    response = client.get('/api/v1/planteles')
    assert response.status_code == 200
    assert isinstance(response.json, list)

    response = client.get(f'/api/v1/planteles/{plantel.id}')
    assert response.status_code == 200
    assert response.json['nombre'] == 'Plantel Público'

    response = client.get('/api/v1/salones')
    assert response.status_code == 200
    assert isinstance(response.json, list)

    response = client.get('/api/v1/equipos')
    assert response.status_code == 200
    assert isinstance(response.json, list)

    response = client.get('/api/v1/programas')
    assert response.status_code == 200
    assert isinstance(response.json, list)

